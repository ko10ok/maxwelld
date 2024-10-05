import asyncio
import sys


async def process_output_till_done(process: asyncio.subprocess.Process, verbose) -> tuple[bytes, bytes]:
    stdout_lines = []
    stderr_lines = []

    async def read_stream(stream, callback, output_list):
        while True:
            line = await stream.readline()
            if line:
                if verbose:
                    callback(line)
                output_list.append(line)
            else:
                break

    tasks = [
        read_stream(process.stdout, lambda line: sys.stdout.buffer.write(b' > ' + line), stdout_lines),
        read_stream(process.stderr, lambda line: sys.stderr.buffer.write(b' > ' + line), stderr_lines)
    ]

    await asyncio.gather(*tasks)
    await process.wait()

    sys.stdout.flush()
    sys.stderr.flush()

    return b''.join(stdout_lines), b''.join(stderr_lines)
