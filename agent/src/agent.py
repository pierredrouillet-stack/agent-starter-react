import logging
import os

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    STTContextOptions,
    TurnHandlingOptions,
    cli,
    inference,
    llm,
    room_io,
)
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import ai_coustics

from memory import parse_user
from personas import DEFAULT_PERSONA, Persona, persona_by_id, resolve_persona
from recorder import (
    CarriedMessage,
    ResumeRequest,
    attach,
    db_path_from_env,
    load_persona,
    load_resume,
    open_db,
    parse_resume,
)

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Dispatch name of this local worker. Must differ from any deployed agent's name.
AGENT_NAME = os.environ.get("AGENT_NAME", "pierre-assistant-dev")


def resolve_resume(
    metadata: str | None,
) -> tuple[ResumeRequest | None, list[CarriedMessage]]:
    """Read the resume request and its earlier messages; any failure means none."""
    request = parse_resume(metadata)
    if request is None:
        return None, []
    path = db_path_from_env()
    if path is None:
        logger.warning("ignoring resume request: CHAT_DB_PATH is not set")
        return None, []
    try:
        conn = open_db(path)
        try:
            return request, load_resume(conn, request)
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("ignoring resume request: %s", exc)
        return None, []


def session_persona(metadata: str | None, resume: ResumeRequest | None) -> Persona:
    """The persona a session runs with.

    A continued or forked session keeps the persona saved with the source
    conversation and ignores the metadata's; any other session uses the metadata's.
    """
    if resume is None:
        return resolve_persona(metadata)
    path = db_path_from_env()
    if path is None:
        return DEFAULT_PERSONA
    try:
        conn = open_db(path)
        try:
            saved = load_persona(conn, resume.conversation_id)
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("could not read the saved persona: %s", exc)
        return DEFAULT_PERSONA
    # A conversation saved before personas existed has none: the default, silently.
    return persona_by_id(saved)


def carried_chat_ctx(carried: list[CarriedMessage]) -> llm.ChatContext:
    """Chat context holding the earlier messages, under their saved ids."""
    chat_ctx = llm.ChatContext()
    for message in carried:
        chat_ctx.add_message(
            role=message.role,  # type: ignore[arg-type]
            content=message.content,
            id=message.id,
            interrupted=message.interrupted,
        )
    return chat_ctx


# Model of the session's TTS; a persona with its own voice reuses it with another voice id.
TTS_MODEL = "fishaudio/s2.1-pro"
DEFAULT_VOICE = "fa4c9eb3dccc4806b382b40d61c6b10a"


class Assistant(Agent):
    def __init__(
        self,
        persona: Persona = DEFAULT_PERSONA,
        chat_ctx: llm.ChatContext | None = None,
    ) -> None:
        super().__init__(
            chat_ctx=chat_ctx if chat_ctx is not None else NOT_GIVEN,
            # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
            # See all available models at https://docs.livekit.io/agents/models/llm/
            llm=persona.llm or inference.LLM(model="google/gemma-4-31b-it"),
            # To use a realtime model instead of a voice pipeline, replace the LLM
            # with a realtime model and remove the STT/TTS from the AgentSession
            # (Note: This is for OpenAI GPT-Live, the recommended speech-to-speech
            # model. For other providers, see https://docs.livekit.io/agents/models/realtime/)
            # Replace the llm argument with the model's LiveKit Inference ID:
            #    llm="openai/gpt-live-1",
            # Only a persona with its own voice overrides the session's TTS.
            tts=(
                inference.TTS(model=TTS_MODEL, voice=persona.voice)
                if persona.voice
                else NOT_GIVEN
            ),
            instructions=persona.full_instructions(),
        )

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using AssemblyAI, Fish Audio, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        # Keyterms bias the STT toward distinctive words it would otherwise misspell.
        # List your own names, brands, and jargon in `keyterms`. Detection additionally
        # extracts terms from the live conversation, such as a caller's name, and applies
        # them once the transcript corroborates the spelling.
        # See more at https://docs.livekit.io/agents/models/stt/keyterms/
        stt_context_options=STTContextOptions(
            keyterms=["LiveKit"],
            keyterm_detection={"enabled": True},
        ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=inference.TTS(model=TTS_MODEL, voice=DEFAULT_VOICE),
        turn_handling=TurnHandlingOptions(
            # The LiveKit turn detector determines when the user is done speaking and the agent should respond.
            # TurnDetector is an end-of-turn model that listens to the user's audio directly, combining
            # semantic understanding with acoustic cues (intonation, pitch, rhythm) for state-of-the-art accuracy.
            # AgentSession supplies the required VAD automatically.
            # See more at https://docs.livekit.io/agents/build/turns
            turn_detection=inference.TurnDetector(),
            # Adaptive interruptions use the turn detector to tell a real interruption from a
            # backchannel like "mhm" or "right", so the agent keeps talking through the latter.
            # This model is on by default on LiveKit Cloud and in dev mode. To use the model elsewhere,
            # uncomment the `interruption` line. Self-hosted usage past the monthly allowance is billed.
            # See https://docs.livekit.io/deploy/admin/quotas-and-limits/#adaptive-interruption-handling for more information.
            # interruption={"mode": "adaptive"},
            # allow the LLM to generate a response while waiting for the end of turn
            # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
            preemptive_generation={"enabled": True},
        ),
        # Expressive mode injects the TTS provider's markup guide into the LLM prompt, so the model
        # emits inline delivery tags (emotion, pacing, non-verbal sounds) that the TTS renders and
        # the transcript never shows. Requires a TTS model that supports markup, such as the Fish
        # Audio model above.
        expressive=True,
    )

    resume, carried = resolve_resume(ctx.job.metadata)
    persona = session_persona(ctx.job.metadata, resume)
    user_id = parse_user(ctx.job.metadata)
    attach(session, ctx, AGENT_NAME, resume, carried, persona.id, user_id)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(persona, carried_chat_ctx(carried) if resume else None),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )

    if resume:
        # Nothing prompts the model when the user arrives, so greet explicitly.
        session.generate_reply(
            instructions=(
                "The user has just returned to an earlier conversation. Welcome them "
                "back in one short sentence that names the topic you were discussing, "
                "without recapping it."
            )
        )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = anam.AvatarSession(
    #     persona_config=anam.PersonaConfig(
    #         name="...",
    #         avatarId="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/anam
    #     ),
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
