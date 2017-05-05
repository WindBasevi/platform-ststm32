# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.

http://www.stm32duino.com
"""

from os.path import isdir, join

from SCons.Script import DefaultEnvironment

import pdb

env = DefaultEnvironment()

#print env.get("CPPDEFINES")

#resolve variant folder from board name
def getVariantFromBoard(boardi):
    var_folder="";

    boardMappings = {
        "bluepill_f103c8":"BLUEPILL",
        "genericSTM32F103CB":"BLUEPILL",
        "genericSTM32F103C8":"BLUEPILL",
        "maple_mini_b20":"MAPLE_MINI",
        "black_F407VE":"BLACK_F407VE",
        "black_F407ZE":"BLACK_F407ZE",
        "black_F407ZG":"BLACK_F407ZG"
    }

    #check board from mappings
    if boardi in boardMappings:
        var_folder=boardMappings[boardi].upper()

    #convert discovery boards
    if boardi[:5].upper()=="DISCO":
        a=boardi.split("_")
        var_folder="DISCOVERY_"+a[1].upper()

    #convert nucleo boards
    if boardi[:6].upper()=="NUCLEO":
        a=boardi.split("_")
        var_folder="NUCLEO"+a[1].upper()

    if var_folder=="":
        print "ERROR: could not get variant folder from board: "+boardi
		#TODO: should assert here ?
    return var_folder;

#HAL MX based Arduino build
def stm32generic():
    print "stm32generic()"
    env = DefaultEnvironment()
    platform = env.PioPlatform()
    board = env.BoardConfig()

    FRAMEWORK_DIR = join(platform.get_package_dir(
        "framework-arduinoSTM32GENERIC"), "STM32")
    FRAMEWORK_VERSION = platform.get_package_version("framework-arduinoSTM32GENERIC")
    assert isdir(FRAMEWORK_DIR)

    #resolve some defines based on board's json file
    mcuseries=board.get('build.mcu')[:7].upper();  #i.e. STM32F4
    mcudefine=board.get('build.mcu')[:11].upper(); #i.e. STM32F407VG
    boardi=env.get("BOARD");

    #map ststm32 board name to stm32generic variant folder for compiling etc.
    var_folder=getVariantFromBoard(boardi)
    print boardi+" --> " + var_folder;

    #print "var_folder="+var_folder;

    #enable FPU for F4 in building and linking
	#this could be moved into genera
    if mcuseries=="STM32F4":
        #print "board is F4"
        env.Append(
        CCFLAGS=[
            "-mfpu=fpv4-sp-d16",
            "-mfloat-abi=hard"
            ],
		LINKFLAGS=[
			"-mfloat-abi=hard",
			"-mfpu=fpv4-sp-d16",
			"-Wl,--entry=Reset_Handler",
			"--specs=nano.specs"
		],
    )

	#
	#flags and defines copied from platform.txt
	#also could be possible to read from actual file and parse them here
	#
    env.Append(
        CXXFLAGS=[
            "-fno-exceptions",
    		"-fno-rtti",
    		"-std=gnu++11",
            "-fno-threadsafe-statics",
            "-w",
            ("-x","c++"),
            "-CC",
        ],
        CFLAGS=[
            "-std=gnu11",
            "-MMD"
        ],
        CCFLAGS=[
            "--param", "max-inline-insns-single=500",
    		"-ffunction-sections",
    		"-fdata-sections",
    		"-mthumb",
    		"--specs=nano.specs",
            "-nostdlib"

        ],
        CPPDEFINES=[
            ("ARDUINO", 10810),
    		mcuseries,
            mcudefine,
            "ARDUINO_ARCH_STM32",
    		("HSE_VALUE", 8000000),
            ("printf","iprintf")
        ],

        CPPPATH=[
    		join(FRAMEWORK_DIR, "cores", "arduino","stm32"),
    		join(FRAMEWORK_DIR, "cores", "arduino"),
    		join(FRAMEWORK_DIR, "cores", "arduino","usb"),
    		join(FRAMEWORK_DIR, "system", "CMSIS"),
    		join(FRAMEWORK_DIR, "system", mcuseries, "CMSIS_Inc"),
            join(FRAMEWORK_DIR, "system", mcuseries, "CMSIS_Src"),
    		join(FRAMEWORK_DIR, "system", mcuseries, "HAL_Inc"),
            join(FRAMEWORK_DIR, "system", mcuseries, "HAL_Src"),
            join(FRAMEWORK_DIR, "system", mcuseries, "stm32_chip"),

            join(FRAMEWORK_DIR, "variants", var_folder),
        ],

        #for ldscript.ld
        LIBPATH=[
            join(FRAMEWORK_DIR, "variants",
                 var_folder)
        ]
    )
   
    env['LDSCRIPT_PATH'] = "ldscript.ld";

	#
	# upload handling copied from stm32duino, probably not relevant for this package
	# copied here for reference, may be better to remove in the future
	#
    if env.subst("$UPLOAD_PROTOCOL") == "dfu":
        if board.id in ("maple", "maple_mini_origin"):
            env.Append(CPPDEFINES=[("VECT_TAB_ADDR", 0x8005000), "SERIAL_USB"])
        else:
            env.Append(CPPDEFINES=[
                ("VECT_TAB_ADDR", 0x8002000), "SERIAL_USB", "GENERIC_BOOTLOADER"])

            if "stm32f103r" in board.get("build.mcu", ""):
                env.Replace(LDSCRIPT_PATH="bootloader.ld")
            elif board.get("upload.boot_version", 0) == 2:
                env.Replace(LDSCRIPT_PATH="bootloader_20.ld")
    else:
        env.Append(CPPDEFINES=[("VECT_TAB_ADDR", 0x8000000)])

    #
    # Lookup for specific core's libraries
    #
    env.Append(
        LIBSOURCE_DIRS=[
            join(FRAMEWORK_DIR, "libraries")
      ]
    )

	#
	# remove unrelevant flags for linking, they originate from build.py which sets defaults
	# for all frameworks: mbed, etc.
	#
    libs = []

    for item in ("-nostartfiles","-nostdlib"):
        if item in env['LINKFLAGS']:
            env['LINKFLAGS'].remove(item)

    for item in ("stdc++","nosys"):
        if item in env['LIBS']:
            env['LIBS'].remove(item)

	#
    # Target: Build Core Library
    #
    libs.append(env.BuildSources(
        join("$BUILD_DIR", "core"),
        join(FRAMEWORK_DIR, "cores", "arduino"))
        )

    libs.append(env.BuildSources(
        join("$BUILD_DIR", "variants", var_folder),
        join(FRAMEWORK_DIR, "variants", var_folder)) )

    #env.Prepend(LIBS=libs)


def stm32duino():
    env = DefaultEnvironment()
    platform = env.PioPlatform()
    board = env.BoardConfig()
    print "stm32duino()";
    if board.id == "bluepill_f103c8":
        board = env.BoardConfig("genericSTM32F103C8")
        env['LDSCRIPT_PATH'] = board.get("build.ldscript")
        env.ProcessFlags(board.get("build.extra_flags"))


    FRAMEWORK_DIR = join(platform.get_package_dir(
        "framework-arduinoststm32"), "STM32F1")
    FRAMEWORK_VERSION = platform.get_package_version("framework-arduinoststm32")
    assert isdir(FRAMEWORK_DIR)

    env.Append(
        CCFLAGS=[
            "--param", "max-inline-insns-single=500",
            "-march=armv7-m"
        ],

        CPPDEFINES=[
            ("ARDUINO", 10610),
            "BOARD_%s" % board.get("build.variant"),
            ("ERROR_LED_PORT", "GPIOB"),
            ("ERROR_LED_PIN", 1),
            ("DEBUG_LEVEL", "DEBUG_NONE"),
            "__STM32F1__",
            "ARDUINO_ARCH_STM32F1"
        ],

        CPPPATH=[
            join(FRAMEWORK_DIR, "cores", board.get("build.core")),
            join(FRAMEWORK_DIR, "system", "libmaple"),
            join(FRAMEWORK_DIR, "system", "libmaple", "include"),
            join(FRAMEWORK_DIR, "system", "libmaple", "usb", "stm32f1"),
            join(FRAMEWORK_DIR, "system", "libmaple", "usb", "usb_lib")
        ],

        LIBPATH=[
            join(FRAMEWORK_DIR, "variants",
                 board.get("build.variant"), "ld")
        ],

        LIBS=["c"]
    )

    for item in ("-nostartfiles", "-nostdlib"):
        if item in env['LINKFLAGS']:
            env['LINKFLAGS'].remove(item)


    if env.subst("$UPLOAD_PROTOCOL") == "dfu":
        if board.id in ("maple", "maple_mini_origin"):
            env.Append(CPPDEFINES=[("VECT_TAB_ADDR", 0x8005000), "SERIAL_USB"])
        else:
            env.Append(CPPDEFINES=[
                ("VECT_TAB_ADDR", 0x8002000), "SERIAL_USB", "GENERIC_BOOTLOADER"])

            if "stm32f103r" in board.get("build.mcu", ""):
                env.Replace(LDSCRIPT_PATH="bootloader.ld")
            elif board.get("upload.boot_version", 0) == 2:
                env.Replace(LDSCRIPT_PATH="bootloader_20.ld")
    else:
        env.Append(CPPDEFINES=[("VECT_TAB_ADDR", 0x8000000)])


    if "__debug" in COMMAND_LINE_TARGETS:
        env.Append(CPPDEFINES=[
            "SERIAL_USB", "GENERIC_BOOTLOADER",
            ("CONFIG_MAPLE_MINI_NO_DISABLE_DEBUG", "1")
        ])

    #
    # Lookup for specific core's libraries
    #

    BOARD_CORELIBDIRNAME = board.get("build.core", "")
    env.Append(
        LIBSOURCE_DIRS=[
            join(FRAMEWORK_DIR, "libraries", "__cores__", BOARD_CORELIBDIRNAME),
            join(FRAMEWORK_DIR, "libraries")
        ]
    )

    #
    # Target: Build Core Library
    #

    libs = []

    if "build.variant" in board:
        env.Append(
            CPPPATH=[
                join(FRAMEWORK_DIR, "variants",
                     board.get("build.variant"))
            ]
        )
        libs.append(env.BuildLibrary(
            join("$BUILD_DIR", "FrameworkArduinoVariant"),
            join(FRAMEWORK_DIR, "variants", board.get("build.variant"))
        ))

    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduino"),
        join(FRAMEWORK_DIR, "cores", board.get("build.core"))
    ))

    env.Prepend(LIBS=libs)

if "USE_STM32GENERIC" in env.get("CPPDEFINES"):
    print "USE STM32GENERIC"
    stm32generic()
else:
    stm32duino()



