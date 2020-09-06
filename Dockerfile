# Portions Copyright 2019 Productize SPRL
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 
#
# This docker configuration was originally based on https://github.com/productize/docker-kicad as of 301bf181b72c811e9644b83a895ec4a16f2fa1a0


FROM ubuntu:focal
LABEL Description="kicad-tools with rest api (using kibot)"

# Use a UTF-8 compatible LANG because KiCad 5 uses UTF-8 in the PCBNew title
# This causes a "failure in conversion from UTF8_STRING to ANSI_X3.4-1968" when
# attempting to look for the window name with xdotool.
ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# Install Kibot

# Kicad's libraries are tied to python3
RUN apt-get -y update && \
    apt-get install -y python3-pip python3-xvfbwrapper python3-psutil fluxbox wmctrl \
    x11vnc ssvnc xvfb recordmydesktop xdotool xclip wget aptitude apt-utils imagemagick software-properties-common

#install latest kicad (cannot use the stock ubuntu kicad package as kibom/bom/sch will fail)
RUN add-apt-repository --yes ppa:kicad/kicad-5.1-releases && \
    apt -y update && \
    apt install -y --install-recommends kicad

#install INTI-CMNB kicad-automation-scripts as a dependency to kibot
RUN wget https://github.com/INTI-CMNB/kicad-automation-scripts/releases/download/v1.4.1/kicad-automation-scripts.inti-cmnb_1.4.1-1_all.deb \
&& apt install ./kicad-automation-scripts.inti-cmnb_*_all.deb 

#install INTI-CMNB Interactive BOM
RUN wget https://github.com/INTI-CMNB/InteractiveHtmlBom/releases/download/v2.3.3/interactivehtmlbom.inti-cmnb_2.3.3-1_all.deb \
&& apt install ./interactivehtmlbom.inti-cmnb_*_all.deb

#copy kibot yaml
COPY ./etc/kibot/. /opt/etc/kibot

#install kibot (supports positions files and png rendering)
RUN pip3 install --no-compile kibot
RUN pip3 install --no-compile pcbdraw


# Copy the installed global symbol and footprint so projects built with stock
# symbols and footprints don't break
#RUN cp /usr/share/kicad/template/sym-lib-table /root/.config/kicad/
#RUN cp /usr/share/kicad/template/fp-lib-table /root/.config/kicad/



# Install REST API
WORKDIR /usr/src/api
COPY ./api/. /usr/src/api
RUN pip3 install -r requirements.txt