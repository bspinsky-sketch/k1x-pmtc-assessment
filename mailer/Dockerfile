# The report mailer, as a Lambda container image.
#
# A container rather than a zip because headless Chromium is the hard
# dependency here: rendering the real Output Report templates to PDF is the
# whole job, and Chromium does not fit a zip package any more than
# LibreOffice did. That is also why this function is separate from
# `PmtcApp`, which stays a small pure-Python zip that needs no Docker at
# deploy time.
#
# 2026-08-31: switched from LibreOffice (converting a python-pptx
# placeholder deck) to Playwright + headless Chromium (rendering the real
# 11-page `output_report/*.tmpl.html` Jinja2 templates directly to PDF).
# See CLAUDE_problems.md and SESSION_LOG.md for the full writeup. Debian
# stays the base image -- proven working here already, and Playwright's own
# install path targets Debian/Ubuntu directly.
FROM debian:bookworm-slim

# python3-pip for the Lambda runtime interface client and this function's
# own dependencies. Chromium's own runtime libraries (fonts, graphics,
# audio/video codecs it links against even headless) are not bundled with
# the pip wheel -- `playwright install --with-deps` below pulls them via
# apt, which is why apt itself has to stay available through that step
# rather than being cleaned up first.
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 \
      python3-pip \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# --break-system-packages because Debian 12 marks the system Python as
# externally managed (PEP 668). In a single-purpose container there is no
# other Python to protect, and a venv would only add a layer and a path to
# remember.
RUN pip3 install --no-cache-dir --break-system-packages \
      awslambdaric==3.1.1 \
      boto3==1.40.19 \
      jinja2==3.1.4 \
      pypdf==5.0.1 \
      playwright==1.47.0

# Where Chromium's own binary lands, set *before* `playwright install` runs
# so the browser is installed here and not under whatever $HOME happens to
# be at build time. This matters specifically because Lambda's `/tmp` is a
# separate ephemeral storage volume mounted fresh at *runtime*, distinct
# from the image's own filesystem layers -- anything written under `/tmp`
# during the build (which is what Playwright's default cache path,
# `~/.cache/ms-playwright`, would resolve to once HOME is set to `/tmp` for
# the LibreOffice-era reason below) would not actually be present when the
# function runs. `/opt` is part of the image itself and is read-only but
# present at runtime, which is exactly what a baked-in browser binary needs.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
RUN playwright install --with-deps chromium

WORKDIR /var/task

COPY mailer/generate.py mailer/handler.py ./
# The 11 locked report templates and their shared assets (CSS, fonts,
# background images, the K1x logo, roadmap_data.js), baked into the image
# so rendering a report needs nothing at runtime beyond what shipped here --
# same principle the old placeholder followed by baking in nothing that
# needed a network call. Build context is the repo root (see
# infra/lib/mail-stack.ts), which is why this path is relative to that root
# rather than to this Dockerfile's own directory.
COPY output_report/ ./output_report/

# Chromium needs somewhere writable for its own runtime profile/cache, and
# everything outside /tmp is read-only on Lambda -- the same reason
# LibreOffice needed this before. generate.py also explicitly creates its
# working directory under /tmp rather than relying on this alone, but
# Chromium's own internal temp usage (independent of that working
# directory) still needs HOME to point somewhere writable.
ENV HOME=/tmp

ENTRYPOINT ["/usr/bin/python3", "-m", "awslambdaric"]
CMD ["handler.handler"]
