import argparse
from collections import namedtuple
import os
import pathlib
import struct
import sys

parser = argparse.ArgumentParser(description='Manage .cpr files.')
parser.add_argument('-i', '--input', nargs="+", type=pathlib.Path, help='Input ROM files')
parser.add_argument('-d', '--details', action='store_true', help='Print details about input files')
parser.add_argument('-o', '--output', type=pathlib.Path, help='Combine input files into a single .cpr file')
parser.add_argument('-b', '--banks', nargs='+', type=int, help='List of banks to use in output')

args = parser.parse_args()

# AMSDOS header format: http://www.cpcwiki.eu/index.php/AMSDOS_Header

o = None
if args.output:
    if os.path.exists(args.output):
        sys.exit("%s already exists" % args.output)
    print("Writing %s" % args.output)
    o = open(args.output, 'wb')
    o.write(b'RIFF')
    # We'll come back and write the size later
    o.write(b'\0\0\0\0')
    o.write(b'AMS!')

chunk_id = -1
def next_chunk():
    global chunk_id
    if args.banks and len(args.banks) > 0:
        chunk_id = args.banks.pop(0)
    else:
        chunk_id += 1

for filename in args.input:
    f = open(filename, 'rb')
    header_data = f.read(0x80)
    Header = namedtuple('Header', 'user filename extension zero block_num last_block type data_location load_adr first_block logical_length entry_adr real_length checksum')
    header = Header._make(struct.unpack('<B8s3s4sBBBHHBHH36x3sH59x', header_data))
    checksum = sum(header_data[0:66])

    bytes_left = header.logical_length
    if args.details:
        print('%s:' % filename)
    if header.checksum == checksum:
        if args.details:
            print('\t%s' % str(header))
    else:
        if args.details:
            print("\tNo header")
        f.seek(0, os.SEEK_END)
        bytes_left = f.tell()
        f.seek(0)

    if o != None:
        next_chunk()
        print('Adding %s (%d bytes) to %s' % (filename, bytes_left, args.output))
        while (bytes_left > 0):
            print("  Writing chunk %d" % chunk_id)
            o.write(b'cb')
            o.write(bytes(str(chunk_id).zfill(2), 'ascii'))
            o.write(min(16384, bytes_left).to_bytes(4, byteorder='little'))
            o.write(f.read(min(16384, bytes_left)))
            bytes_left -= min(16384, bytes_left)
            if bytes_left > 0:
                chunk_id += 1

    f.close()

if o:
    # Go back to the start and write the correct size
    cpr_len = o.tell() - 8
    o.close()
    print("Writing size (%d) to cpr" % cpr_len)
    o = open(args.output, 'r+b')
    o.seek(4)
    o.write(cpr_len.to_bytes(4, byteorder='little'))
    o.close();