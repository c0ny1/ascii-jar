import os
import argparse
import io
import struct
from typing import Union
from enum import Enum


class ZIPTag(Enum):
    S_ZIPFILERECORD = 0x04034b50
    S_ZIPDATADESCR = 0x08074b50
    S_ZIPDIRENTRY = 0x02014b50
    S_ZIPDIGITALSIG = 0x05054b50
    S_ZIP64ENDLOCATORRECORD = 0x06064b50
    S_ZIP64ENDLOCATOR = 0x07064b50
    S_ZIPENDLOCATOR = 0x06054b50


class ZIPManipulation(object):
    def __init__(self, reader: Union[io.BytesIO, bytes], prepend: bytes, append: bytes):
        if isinstance(reader, bytes):
            reader = io.BytesIO(reader)

        self.reader: io.BytesIO = reader
        self.prepend_table = []
        self.append_table = []
        self.prepend = prepend
        self.prepend_size = len(prepend)
        self.append = append
        self.append_size = len(append)

    def run(self):
        while True:
            tag = self.reader.read(4)
            length = len(tag)
            if length == 0:
                break
            elif length > 4:
                raise Exception('please do not append any bytes to original zip file')
            elif length < 4:
                raise Exception('unsupported type found')

            n = struct.unpack('<I', tag)
            self.next(n[0])

        self.reader.seek(0)
        data = self.reader.getvalue()
        for (index, offset) in self.prepend_table:
            data = data[:index] + struct.pack('<I', offset + self.prepend_size) + data[index + 4:]

        for (index, size) in self.append_table:
            data = data[:index] + struct.pack('<H', size + self.append_size) + data[index + 2:]

        return self.prepend + data + self.append

    def next(self, tag: int):
        if tag == ZIPTag.S_ZIPFILERECORD.value:
            self.zip_filerecord()
        elif tag == ZIPTag.S_ZIPDATADESCR.value:
            self.zip_data_descr()
        elif tag == ZIPTag.S_ZIPDIRENTRY.value:
            self.zip_direntry()
        elif tag == ZIPTag.S_ZIPENDLOCATOR.value:
            self.zip_end_locator()
        else:
            raise Exception('does not support this type of zip: %r', tag)

    def zip_filerecord(self):
        self.reader.read(14)
        compressed_size = struct.unpack('<I', self.reader.read(4))[0]
        self.reader.read(4)
        filename_size, extra_size = struct.unpack('<HH', self.reader.read(4))
        self.reader.read(compressed_size + filename_size + extra_size)

    def zip_data_descr(self):
        self.reader.read(12)

    def zip_direntry(self):
        self.reader.read(24)
        filename_size = struct.unpack('<H', self.reader.read(2))[0]
        self.reader.read(12)
        index = self.reader.tell()
        offset = struct.unpack('<I', self.reader.read(4))[0]
        self.reader.read(filename_size)

        self.prepend_table.append((index, offset))

    def zip_end_locator(self):
        self.reader.read(12)
        index = self.reader.tell()
        offset, comment_size = struct.unpack('<IH', self.reader.read(6))
        self.prepend_table.append((index, offset))
        self.append_table.append((index + 4, comment_size))


def main():
    parser = argparse.ArgumentParser(
        description='A tool you can craft a zip file that contains the padding characters between the file content'
    )
    parser.add_argument('-i', '--input', required=True, metavar='INPUT_FILENAME')
    parser.add_argument('-o', '--output', required=True, metavar='OUTPUT_FILENAME')
    parser.add_argument('-p',
                        '--prepend',
                        help='the characters that you want to prepend to the file beginning')
    parser.add_argument('-a',
                        '--append',
                        help='the characters that you want to append to the file')
    args = parser.parse_args()

    with open(args.input, 'rb') as f:
        data = f.read()

    manipulation = ZIPManipulation(data, args.prepend.encode(), args.append.encode())
    data = manipulation.run()

    with open(args.output, 'wb') as f:
        f.write(data)

    print('file %r is generated' % args.output)


if __name__ == '__main__':
    main()