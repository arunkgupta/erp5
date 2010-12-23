# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import re
import shutil
from os.path import join, basename

from zope.interface import implements

from Products.PortalTransforms.libtransforms.utils import bin_search, sansext, getShortPathName
from Products.PortalTransforms.interfaces import ITransform

class commandtransform:
    """abstract class for external command based transform
    """
    implements(ITransform)

    def __init__(self, name=None, binary=None, **kwargs):
        if name is not None:
            self.__name__ = name
        if binary is not None:
            self.binary = bin_search(binary)
            self.binary = getShortPathName(self.binary)

    def name(self):
        return self.__name__

    def initialize_tmpdir(self, data, **kwargs):
        """create a temporary directory, copy input in a file there
        return the path of the tmp dir and of the input file
        """
        tmpdir = tempfile.mktemp()
        os.mkdir(tmpdir)
        filename = kwargs.get("filename", '')
        fullname = join(tmpdir, basename(filename))
        filedest = open(fullname , "wb").write(data)
        return tmpdir, fullname

    def subObjects(self, tmpdir):
        imgs = []
        for f in os.listdir(tmpdir):
            result = re.match("^.+\.(?P<ext>.+)$", f)
            if result is not None:
                ext = result.group('ext')
                if ext in ('png', 'jpg', 'gif'):
                    imgs.append(f)
        path = join(tmpdir, '')
        return path, imgs

    def fixImages(self, path, images, objects):
        for image in images:
            objects[image] = open(join(path, image), 'rb').read()

    def cleanDir(self, tmpdir):
        shutil.rmtree(tmpdir)

class popentransform:
    """abstract class for external command based transform

    Command must read from stdin and write to stdout
    """
    implements(ITransform)

    binaryName = ""
    binaryArgs = ""
    useStdin = True

    def __init__(self, name=None, binary=None, binaryArgs=None, useStdin=None,
                 **kwargs):
        if name is not None:
            self.__name__ = name
        if binary is not None:
            self.binary = bin_search(binary)
        else:
            self.binary = bin_search(self.binaryName)
        if binaryArgs is not None:
            self.binaryArgs = binaryArgs
        if useStdin is not None:
            self.useStdin = useStdin

    def name(self):
        return self.__name__

    def getData(self, couterr):
        return couterr.read()

    def convert(self, data, cache, **kwargs):
        command = "%s %s" % (self.binary, self.binaryArgs)
        if not self.useStdin:
            tmpfile, tmpname = tempfile.mkstemp(text=False) # create tmp
            os.write(tmpfile, data) # write data to tmp using a file descriptor
            os.close(tmpfile)       # close it so the other process can read it
            command = command % { 'infile' : tmpname } # apply tmp name to command

        cin, couterr = os.popen4(command, 'b')

        if self.useStdin:
            cin.write(str(data))

        status = cin.close()

        out = self.getData(couterr)
        couterr.close()

        if not self.useStdin:
            # remove tmp file
            os.unlink(tmpname)

        cache.setData(out)
        return cache

from subprocess import Popen, PIPE
import shlex

class subprocesstransform:
    """abstract class for subprocess command based transform

    Command must read from stdin and write to stdout
    """
    implements(ITransform)

    binaryName = ""
    binaryArgs = ""
    useStdin = True

    def __init__(self, name=None, binary=None, binaryArgs=None, useStdin=None,
                 **kwargs):
        if name is not None:
            self.__name__ = name
        if binary is not None:
            self.binary = bin_search(binary)
        else:
            self.binary = bin_search(self.binaryName)
        if binaryArgs is not None:
            self.binaryArgs = binaryArgs
        if useStdin is not None:
            self.useStdin = useStdin

    def name(self):
        return self.__name__

    def getData(self, couterr):
        return couterr.read()

    def convert(self, data, cache, **kwargs):
        command = "%s %s" % (self.binary, self.binaryArgs)

        if self.useStdin:
          tempfile_object = tempfile.NamedTemporaryFile()
          tmpname = tempfile_object.name
          tempfile_object.write( data)
          tempfile_object.seek(0)
          command = command % {'infile': tmpname} # apply tmp name to command
        argument_list = shlex.split(command)
        if self.useStdin:
          process = Popen(argument_list, stdin=tempfile_object, stdout=PIPE,
                          stderr=PIPE, close_fds=True)
          data_out, data_err = process.communicate()
          tempfile_object.close()
        else:
          process = Popen(argument_list, stdin=PIPE, stdout=PIPE,
                          stderr=PIPE, close_fds=True)
          data_out, data_err = process.communicate(input=data)
        if data_err:
          raise OSError, data_err
        cache.setData(data_out)
        return cache
