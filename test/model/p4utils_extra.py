from p4utils.mininetlib.node import Tofino
from p4utils.utils.compiler import *
from p4utils.utils.helper import *
import pprint

class Tofino1(Tofino):
    pass
class Tofino2(Tofino):
    def add_tofino_args(self):
        args = super().add_tofino_args()
        args.insert(1, '--arch tf2')
        return args
    def add_driver_args(self):
        args = super().add_driver_args()
        args.insert(1, '--arch tf2')
        return args

class Tofino1P4C(BF_P4C):
    pass
class Tofino2P4C(BF_P4C):
    def compile(self):
        """Compiles the P4 file and generates the configuration files."""
        # Compute checksum of P4 file. This allows to recognize modified files.
        self.cksum = cksum(self.p4_src)
        debug('source: {}\tcksum: {}\n'.format(self.p4_src, self.cksum))

        # Set environmental variables
        cmd = 'export SDE={} && '.format(self.sde)
        cmd += 'export SDE_INSTALL={} && '.format(self.sde_install)

        # manual cmake
        if not self.build_script:
            cmd += 'cd {}; '.format(self.build_dir)
            cmd += 'cmake $SDE/p4studio/ -DCMAKE_INSTALL_PREFIX=$SDE/install ' + \
                '-DCMAKE_MODULE_PATH=$SDE/cmake  -DP4_NAME={} '.format(self.p4_name) + \
                '-DTOFINO2=ON ' + '-DP4_PATH={} && '.format(self.p4_src)
            cmd += 'make {} && make install'.format(self.p4_name)
        # if we use the p4_build script
        else:
            cmd += '{} --with-tofino2 {}'.format(self.build_script, self.p4_src)

        debug(cmd + '\n')

        # Execute command
        p = subprocess.Popen(cmd,
                             shell=True,
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        stdout, stderr = p.communicate()

        if p.returncode != 0:
            info(stdout.decode(errors='backslashreplace'))
            error(stderr.decode(errors='backslashreplace'))
            raise CompilationError
        else:
            if len(stderr) == 0:
                info('{} compiled successfully.\n'.format(self.p4_src))
                info(stdout.decode(errors='backslashreplace'))
            else:
                info('{} compiled with warnings.\n'.format(self.p4_src))
                info(stdout.decode(errors='backslashreplace'))
                warning(stderr.decode(errors='backslashreplace'))
            self.compiled = True