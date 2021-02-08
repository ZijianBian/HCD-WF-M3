from contextlib import contextmanager
import ctypes
import io
import os
import sys
import tempfile

libc = ctypes.CDLL(None)
c_stdout = ctypes.c_void_p.in_dll(libc, "stdout")


@contextmanager
def stdout_redirector(stream):
    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stdout_fd = sys.stdout.fileno()

    def _redirect_stdout(to_fd):
        """Redirect stdout to the given file descriptor."""
        # Flush the C-level buffer stdout
        libc.fflush(c_stdout)
        # Flush and close sys.stdout - also closes the file descriptor (fd)
        sys.stdout.close()
        # Make original_stdout_fd point to the same file as to_fd
        os.dup2(to_fd, original_stdout_fd)
        # Create a new sys.stdout that points to the redirected fd
        sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, "wb"))

    # Save a copy of the original stdout fd in saved_stdout_fd
    saved_stdout_fd = os.dup(original_stdout_fd)
    try:
        # Create a temporary file and redirect stdout to it
        tfile = tempfile.TemporaryFile(mode="w+b")
        _redirect_stdout(tfile.fileno())
        # Yield to caller, then redirect stdout back to the saved fd
        yield
        _redirect_stdout(saved_stdout_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stdout_fd)


def redirect_stdout(fstdout):
    sys.stdout.flush()  # <--- important when redirecting to files
    oldstdout = os.dup(1)

    # stdnew = os.open(os.devnull, os.O_WRONLY)
    # newstdout = os.open(fstdout, os.O_RDWR|os.O_CREAT )
    newstdout = os.open(fstdout, os.O_APPEND | os.O_CREAT | os.O_WRONLY)

    os.dup2(newstdout, 1)
    return (
        oldstdout,
        newstdout,
    )


def stdout_back(oldstdout, newstdout):

    os.dup2(oldstdout, 1)
    os.close(newstdout)


#    sys.stdout = os.fdopen(newstdout, 'w')
