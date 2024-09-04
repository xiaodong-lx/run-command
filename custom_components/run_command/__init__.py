from .const import *
import asyncio
import logging
from homeassistant.core import ServiceResponse, SupportsResponse
from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError

LOGGER = logging.getLogger(__package__)

# https://github.com/home-assistant/core/blob/dev/homeassistant/components/command_line/utils.py
async def async_check_output_or_log(command: str, timeout: int) -> str | None:
    # Run a shell command with a timeout and return the output.
    try:
        proc = await asyncio.create_subprocess_shell(  # shell by design
            command,
            close_fds = False,  # required for posix_spawn
            stdout = asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(timeout):
            stdout, _ = await proc.communicate()

        if proc.returncode != 0:
            LOGGER.error(
                "Command failed (with return code %s): %s", proc.returncode, command
            )
        else:
            return stdout.strip().decode("utf-8")
    except TimeoutError:
        LOGGER.error("Timeout for command: %s", command)

    return None

async def async_setup_entry(hass, config):

    # https://github.com/home-assistant/core/blob/dev/homeassistant/components/command_line/sensor.py
    async def service_run(call) -> ServiceResponse:
        command = call.data.get("command")
        timeout = call.data.get("timeout")

        if " " not in command:
            prog = command
            args = None
            args_compiled = None
        else:
            prog, args = command.split(" ", 1)
            args_compiled = Template(args, hass)

        if args_compiled:
            try:
                args_to_render = {"arguments": args}
                rendered_args = args_compiled.async_render(args_to_render)
            except TemplateError as ex:
                LOGGER.exception("Error rendering command template: %s", ex)
                return
        else:
            rendered_args = None

        if rendered_args == args:
            # No template used. default behavior
            pass
        else:
            # Template used. Construct the string used in the shell
            command = f"{prog} {rendered_args}"

        LOGGER.debug("Running command: %s", command)

        return {
            "result": await async_check_output_or_log(command, timeout)
        }

    hass.services.async_register(DOMAIN, "run", service_run, supports_response=SupportsResponse.OPTIONAL)
        
    return True
