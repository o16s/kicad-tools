#!/usr/bin/env python

#   Copyright 2015-2016 Scott Bezek and the splitflap contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import os
import subprocess
import sys
import time
import argparse

from time import sleep

from contextlib import contextmanager


eeschema_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(eeschema_dir)

sys.path.append(repo_root)

from xvfbwrapper import Xvfb
from util import file_util
from util.ui_automation import (
    PopenContext,
    xdotool,
    wait_for_window,
    recorded_xvfb,
    clipboard_store,
    clipboard_retrieve
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def dismiss_library_error():
    # The "Error" modal pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    # There -should- be a way to disable it, but I haven't the magic to drop in the config file yet
    try:
        nf_title = 'Error'
        wait_for_window(nf_title, nf_title, 3)

        logger.info('Dismiss eeschema library warning modal')
        xdotool(['search', '--onlyvisible', '--name', nf_title, 'windowfocus'])
        xdotool(['key', 'Escape'])
    except RuntimeError:
        pass

def dismiss_library_warning():
    # The "Not Found" window pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    try:
        nf_title = 'Not Found'
        wait_for_window(nf_title, nf_title, 3)

        logger.info('Dismiss eeschema library warning window')
        xdotool(['search', '--onlyvisible', '--name', nf_title, 'windowfocus'])
        xdotool(['key', 'Return'])
    except RuntimeError:
        pass

def dismiss_newer_version():
    # The "Not Found" window pops up if libraries required by the schematic have
    # not been found. This can be ignored as all symbols are placed inside the
    # *-cache.lib file:
    try:
        logger.info('Dismiss schematic version notification')
        wait_for_window('Newer schematic version notification', 'Info', 3)

        xdotool(['key', 'Return'])
    except RuntimeError:
        pass


def dismiss_remap_helper():
    # The "Remap Symbols" windows pop up if the uses the project symbol library
    # the older list look up method for loading library symbols.
    # This can be ignored as we're just trying to output data and don't
    # want to mess with the actual project.
    try:
        logger.info('Dismiss schematic symbol remapping')
        wait_for_window('Remap Symbols', 'Remap', 3)

        xdotool(['key', 'Escape'])
    except RuntimeError:
        pass





def eeschema_export_bom(output_dir, eeschema_proc):
    bom_file = output_dir + "bom.csv"
    clipboard_store('xsltproc -o "'+bom_file + '" "/usr/share/kicad/plugins/bom2grouped_csv.xsl" "%I"');

    dismiss_newer_version()
    dismiss_remap_helper()
    dismiss_library_warning()
    dismiss_library_error()

    wait_for_window('eeschema', '.sch')

    logger.info('Focus main eeschema window')
    xdotool(['search', '--onlyvisible', '--name', '.sch', 'windowfocus'])

    logger.info('Open Tools->Generate Bill Of Materials')
    xdotool(['key', 'alt+t'])
    xdotool(['key', 'm'])

    logger.info('Run generate')
    wait_for_window('plot', 'Bill of Material')
    xdotool(['search', '--name', 'Bill of Material', 'windowfocus'])
    logger.info("Select commandline window");
    xdotool(['key', 'Tab',
                'Tab',
                'Tab',
                'Tab',
                'Tab',
                'Tab']);

    logger.info('Paste xslt command')
    xdotool(['key', 'ctrl+v'])
    xdotool(['key', 'Tab'])
    xdotool(['key', 'space'])
    logger.info("Waiting for bom file")
    # this might take a moment. Wait for the bom.csv to appear
    file_util.wait_for_file_created_by_process(eeschema_proc.pid, bom_file)
    # Seems to be a bit of a delay here
    sleep(2)
    logger.info('Closing BOM dialog')
    xdotool(['key', 'Tab'])
    xdotool(['key', 'Tab'])
    xdotool(['key', 'Escape'])
    logger.info('Quitting eeschema')
    wait_for_window('eeschema', '.sch')
    logger.info('Focus main eeschema window')
    xdotool(['search', '--onlyvisible', '--name', '.sch', 'windowfocus'])
    logger.info('Pressing Control+q');
    xdotool(['key', 'Ctrl+q'])
    logger.info('Done!');

def export_bom(schematic_file, output_dir, screencast_dir):

    if screencast_dir:
    	screencast_output_file = os.path.join(screencast_dir, 'export_bom_screencast.ogv')
        with recorded_xvfb(screencast_output_file, width=800, height=600, colordepth=24):
            with PopenContext(['eeschema', schematic_file], close_fds=True) as eeschema_proc:
                eeschema_export_bom(output_dir, eeschema_proc)
    else:
        with Xvfb(width=800, height=600, colordepth=24):
            with PopenContext(['eeschema', schematic_file], close_fds=True) as eeschema_proc:
                eeschema_export_bom(output_dir, eeschema_proc)
    #logger.info('Convert component XML to useful BOM CSV file...')
    #subprocess.check_call([
    #    'python',
    #    '-u',
    #    os.path.join(electronics_root, 'bom', 'generate_bom_csv.py'),
    #    os.path.join(electronics_root, 'splitflap.xml'),
    #    os.path.join(output_dir, 'bom.csv'),
    #])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='KiCad BOM generation automation')
    subparsers = parser.add_subparsers(help='Command:', dest='command')

    parser.add_argument('--schematic', help='KiCad schematic file')
    parser.add_argument('--output_dir', help='output directory')
    parser.add_argument('--screencast_dir', help='Where to record a screencast. No dir = no screencast', default=None)

    export_parser = subparsers.add_parser('export', help='Export the BOM')
    
    args = parser.parse_args()

    if not os.path.isfile(args.schematic):
        logging.error(args.schematic+' does not exist')
        exit(-1)

    output_dir = os.path.abspath(args.output_dir)+'/'
    file_util.mkdir_p(output_dir)

    if args.command == 'export':
        export_bom(args.schematic, output_dir, args.screencast_dir)
        exit(0)
    else:
        usage()
        if sys.argv[1] == 'help':
            exit(0)
    exit(-1)

