# -*- coding: utf-8  -*-
#
# Copyright (C) 2022 DSR! <xchwarze@gmail.com>
# Released under the terms of the MIT License
# Developed for Python 3.6+
# pip install py7zr pywin32 colorama

import argparse
import pathlib
import os
import re
import py7zr
import win32file
import colorama


def is_64bit_pe(name, file_path):
    try:
        is_64bit = win32file.GetBinaryType(str(file_path)) == 6
    except:
        is_64bit = False

    return {
        'name': f'{name} x64' if is_64bit else name,
        'check': 'Check: Is64BitInstallMode;' if is_64bit else '',
    }


def component_name(name):
    return re.sub('[^a-zA-Z0-9 \n]', '', name).replace(' ', '').lower()



class GenerateInstall:
    def __init__(self):
        self.base_path = ''
        self.section_name = ''
        self.tool_name = ''
        self.section_list = []
        self.fix_tool_exe_list = {
            # fix to support main executable
            '[dotnet] dnspyex': ['dnspy.exe'],
            'ollydbg 1.10': ['ollydbg.exe'],
            'winhex': ['winhex.exe'],
            'astrogrep': ['astrogrep.exe'],
            'rl!depacker': ['rl!depacker.exe'],

            # support also the x64 versions
            'hxd': ['hxd32.exe', 'hxd64.exe'],
            'api monitor': ['apimonitor-x86.exe', 'apimonitor-x64.exe'],
            'autoruns': ['autoruns.exe', 'autoruns64.exe'],
            'process explorer': ['procexp.exe', 'procexp64.exe'],
            'process hacker 2': ['processhacker.exe'],
            'process hacker 3': ['processhacker.exe'],
            'procmon': ['procmon.exe', 'procmon64.exe'],
            'regshot': ['regshot-x86-ansi.exe', 'regshot-x64-ansi.exe'],
            'sysanalyzer': ['sysanalyzer.exe', 'hxd64.exe'],
            'tcpview': ['tcpview.exe', 'tcpview64.exe'],
            'process-dump': ['pd32.exe', 'pd64.exe'],
            'scylla': ['scylla_x86.exe', 'scylla_x64.exe'],
            'strings': ['strings.exe', 'strings64.exe'],
            'de4dot': ['de4dot.exe', 'de4dot-x64.exe'],
            'netunpack': ['netunpack.exe', 'netunpack-64.exe'],
        }
        self.compact_tool_list = [
            # analysis
            'die', 'exeinfope', 'pestudio',

            # decompilers
            '[android] jadx', '[java] recaf', '[dotnet] ilspy',

            # dissasembler
            'x64dbg',

            # hex editor
            'hxd', 'imhex',

            # monitor
            'process hacker 3', 'procmon', 'tcpview',

            # other
            'hashcalc', 'resource hacker', 'virustotaluploader',

            # rootkits detector
            'gmer', 'sysinspector',

            # unpacking
            'qunpack', 'rl!depacker', 'uniextract',  'XVolkolak',
        ]
        self.disable_unpack = [
            # decompilers
            'graywolf - 1.83.7z',

            # dissasembler
            '[++] w32dasm - 8.93.7z', '[10] w32dasm - 8.93.7z', '[original] w32dasm - 8.93.7z',

            # unpacking
            'qunpack - 2.2.7z', 'qunpack - 3.4.7z', 'qunpack - src.7z',
        ]

    # helpers
    def absolute_to_local_path(self, path):
        return str(path).replace(f'{str(self.base_path)}\\', '')

    def iss_types(self, name):
        if name.lower() in self.compact_tool_list:
            return 'full compact'

        return 'full'

    # script steps
    def iterate_sections(self, folder_path):
        valid_folders = [
            'analysis', 'decompilers', 'dissasembler', 'hex editor',
            'monitor', 'other', 'rootkits detector', 'unpacking'
        ]
        self.base_path = folder_path
        for item in pathlib.Path(folder_path).iterdir():
            if item.is_dir() & (item.name.lower() in valid_folders):
                self.section_name = item.name
                self.section_list = []
                self.iterate_folder(item)

                section_name = item.name.lower().replace(' ', '-')
                with open(f'sections\\{section_name}.iss', 'w') as file:
                    file.writelines('\n'.join(self.section_list))

    def iterate_folder(self, folder_path):
        for item in pathlib.Path(folder_path).iterdir():
            if item.is_dir():
                print(colorama.Fore.YELLOW + f'[+] Process: {item.name}')
                self.tool_name = item.name

                self.iterate_tool(item)
                self.section_list.append('')
                self.section_list.append('')

    def iterate_tool(self, folder_path, is_sub_folder = False):
        # unpack
        for item in folder_path.glob('*.7z'):
            self.iterate_tool_unpack(item, folder_path)

        # main data
        if not is_sub_folder:
            self.section_list.append(f'; {self.tool_name}')
            self.section_list.append('[Components]')
            self.section_list.append(
                f'Name: "{component_name(self.section_name)}\\{component_name(self.tool_name)}"; '
                f'Description: "{self.tool_name}"; '
                f'Types: {self.iss_types(self.tool_name)}; '
            )
            self.section_list.append('')

            self.section_list.append('[Files]')
            self.section_list.append(
                f'Source: "{{#MySrcDir}}\\toolkit\\{self.absolute_to_local_path(folder_path.absolute())}\\*"; '
                f'DestDir: "{{#MyAppToolsFolder}}\\{self.section_name}\\{self.tool_name}"; '
                f'Components: "{component_name(self.section_name)}\\{component_name(self.tool_name)}"; '
                'Flags: ignoreversion recursesubdirs createallsubdirs; '
            )
            self.section_list.append('')

        # generate executable info
        tool_exe_total = self.iterate_tool_exe(folder_path)
        tool_jar_total = self.iterate_tool_jar(folder_path)

        # iterate sub folders
        for item in pathlib.Path(folder_path).iterdir():
            if item.is_dir() & (tool_exe_total == 0) & (tool_jar_total == 0):
                print(colorama.Fore.MAGENTA + f'   [!] Iterate sub folder: "{item}"')
                self.iterate_tool(item, True)

    def iterate_tool_unpack(self, file_path, folder_path):
        if file_path.name.lower() not in self.disable_unpack:
            if len(os.listdir(folder_path)) > 1:
                # In addition to creating the new directory, change the path of the folder_path
                folder_path = pathlib.Path(folder_path).joinpath(file_path.stem)
                pathlib.Path(folder_path).mkdir(exist_ok=True)

            with py7zr.SevenZipFile(file_path, 'r') as compressed:
                compressed.extractall(folder_path)

            file_path.unlink()

    def iterate_tool_exe(self, folder_path):
        is_first_set = False
        exe_list_len = len(list(folder_path.glob('*.exe')))
        for item in folder_path.glob('*.exe'):
            if exe_list_len > 1:
                if self.tool_name.lower() in self.fix_tool_exe_list.keys():
                    if item.name.lower() in self.fix_tool_exe_list[self.tool_name.lower()]:
                        self.iterate_tool_exe_gen(item)

                elif not is_first_set:
                    print(colorama.Fore.MAGENTA + f'   [!!!] Find multiple exes. Grabbing the first!')
                    is_first_set = True
                    self.iterate_tool_exe_gen(item)

            else:
                self.iterate_tool_exe_gen(item)

        return exe_list_len

    def iterate_tool_exe_gen(self, exe_path):
        print(colorama.Fore.GREEN + f'   [*] Adding: "{str(pathlib.Path(exe_path).name)}"')
        tool_exe_path = self.absolute_to_local_path(exe_path)
        working_dir = str(pathlib.Path(exe_path).parent)
        pe_data = is_64bit_pe(self.tool_name, exe_path)

        self.section_list.append('[Icons]')
        self.section_list.append(
            f'Name: "{{group}}\\{{#MyAppName}}\\{pe_data["name"]}"; '
            f'Filename: "{{#MyAppToolsFolder}}\\{tool_exe_path}"; '
            f'WorkingDir: "{{#MyAppToolsFolder}}\\{self.absolute_to_local_path(working_dir)}"; '
            f'Components: "{component_name(self.section_name)}\\{component_name(self.tool_name)}"; '
            f'{pe_data["check"]}'
        )
        self.section_list.append(
            f'Name: "{{#MyAppBinsFolder}}\\sendto\\sendto\\{self.section_name}\\{pe_data["name"]}"; '
            f'Filename: "{{#MyAppToolsFolder}}\\{tool_exe_path}"; '
            f'WorkingDir: "{{#MyAppToolsFolder}}\\{self.absolute_to_local_path(working_dir)}"; '
            f'Components: "{component_name(self.section_name)}\\{component_name(self.tool_name)}"; '
            f'{pe_data["check"]}'
        )
        self.section_list.append('')

    def iterate_tool_jar(self, folder_path):
        jar_list = list(folder_path.glob('*.jar'))

        # for now there is always 1
        if len(jar_list) == 0:
            return 0

        self.iterate_tool_jar_gen(jar_list[0])

        return len(jar_list)

    def iterate_tool_jar_gen(self, jar_path):
        print(colorama.Fore.GREEN + f'   [*] Adding: "{str(pathlib.Path(jar_path).name)}"')
        tool_jar_path = self.absolute_to_local_path(jar_path)
        working_dir = str(pathlib.Path(jar_path).parent)

        self.section_list.append('[Icons]')
        self.section_list.append(
            f'Name: "{{group}}\\{{#MyAppName}}\\{self.tool_name}"; '
            # f'Filename: "java -jar {{#MyAppToolsFolder}}\\{tool_jar_path}"; '
            f'Filename: "{{#MyAppToolsFolder}}\\{tool_jar_path}"; '
            f'WorkingDir: "{{#MyAppToolsFolder}}\\{self.absolute_to_local_path(working_dir)}"; '
            f'Components: "{component_name(self.section_name)}\\{component_name(self.tool_name)}"; '
            # f'IconFilename: "{{#MyAppToolsFolder}}\\{self.absolute_to_local_path(working_dir)}\\icon.ico";'
        )
        self.section_list.append(
            f'Name: "{{#MyAppBinsFolder}}\\sendto\\sendto\\{self.section_name}\\{self.tool_name}"; '
            # f'Filename: "java -jar {{#MyAppToolsFolder}}\\{tool_jar_path}"; '
            f'Filename: "{{#MyAppToolsFolder}}\\{tool_jar_path}"; '
            f'WorkingDir: "{{#MyAppToolsFolder}}\\{self.absolute_to_local_path(working_dir)}"; '
            f'Components: "{component_name(self.section_name)}\\{component_name(self.tool_name)}"; '
            # f'IconFilename: "{{#MyAppToolsFolder}}\\{self.absolute_to_local_path(working_dir)}\\icon.ico";'
        )
        self.section_list.append('')

    def main(self):
        colorama.init(autoreset=True)

        parser = argparse.ArgumentParser(
            usage='%(prog)s [ARGUMENTS]',
        )
        parser.add_argument(
            '-f',
            '--folder',
            dest='toolkit_folder',
            help='path to toolkit folder',
            type=pathlib.Path,
            required=True,
        )

        arguments = parser.parse_args()
        toolkit_folder = arguments.toolkit_folder
        if not toolkit_folder.is_dir():
            print(colorama.Fore.RED + 'toolkit_folder is not a valid folder')
            return 0

        self.iterate_sections(toolkit_folder)


# se fini
if __name__ == '__main__':
    GenerateInstall().main()
