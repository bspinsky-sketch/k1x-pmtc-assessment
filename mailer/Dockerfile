# The report mailer, as a Lambda container image.
#
# A container rather than a zip because LibreOffice is the hard dependency
# here: turning the filled deck into a PDF is the whole job, LibreOffice is
# the only thing that does it faithfully, and it does not fit a zip package.
# That is also why this function is separate from `PmtcApp`, which stays a
# small pure-Python zip that needs no Docker at deploy time.
#
# Debian rather than the AWS Python base image, following the same reasoning
# proven on the sibling SMOMA project: LibreOffice is packaged for Debian and
# was verified working there. Using an arbitrary base image on Lambda is
# supported -- `awslambdaric` is the runtime interface client that makes any
# image speak Lambda's protocol.
FROM debian:bookworm-slim

# LibreOffice, and only the part that opens presentations. Writer and Calc are
# several hundred megabytes this never touches.
#
# The fonts matter as much as the converter, and this is the lesson that cost
# the sibling project a render: with none of these installed, fontconfig
# answers an unknown family with Liberation Mono, and every heading in the
# report comes out as typewriter text at widths nothing was laid out for.
# Carlito and Liberation Sans are metric-compatible stand-ins for Calibri and
# Arial, so anything using those two keeps its line breaks exactly.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-impress \
      fonts-crosextra-carlito \
      fonts-liberation2 \
      fontconfig \
      python3 \
      python3-pip \
 && rm -rf /var/lib/apt/lists/*

# What to substitute for the families this image does not have. See the file.
COPY fonts.conf /etc/fonts/conf.d/99-pmtc.conf
RUN fc-cache -f

# --break-system-packages because Debian 12 marks the system Python as
# externally managed (PEP 668). In a single-purpose container there is no
# other Python to protect, and a venv would only add a layer and a path to
# remember.
RUN pip3 install --no-cache-dir --break-system-packages \
      awslambdaric==3.1.1 \
      python-pptx==1.0.2 \
      boto3==1.40.19

WORKDIR /var/task

COPY generate.py handler.py ./

# When Ben's template lands it is baked in here, alongside the code that
# fills it, so the deck and the filling code are one artifact and cannot be
# at different versions:
#
#     COPY master.pptx ./
#
# See README.md, "When the real deck arrives".

# LibreOffice wants somewhere to write a user profile, and everything outside
# /tmp is read-only on Lambda. Without this it fails on the first conversion
# with an error that does not mention the filesystem.
ENV HOME=/tmp

ENTRYPOINT ["/usr/bin/python3", "-m", "awslambdaric"]
CMD ["handler.handler"]
