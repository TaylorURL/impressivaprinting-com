#!/usr/bin/env python3
"""Drops the clean aperture property out of an AVIF file, in place.

macOS ImageIO writes a `clap` into every AVIF it encodes, marks it essential,
and sets it to the frame the picture already is less one row or column. It
crops nothing anybody asked for. But essential means essential: a reader that
does not implement clean aperture is required to refuse the whole item rather
than ignore the property it does not know, so a file carrying one decodes in
some browsers and fails outright in others while answering perfectly on the
wire. A picture that loads for most of the web and for nobody on Firefox is the
shape that leaves behind.

The AV1 bitstream is not touched. The property is removed from the container's
property container, every item's associations are rewritten to match, and the
bytes that frees are handed to a `free` box at the end of the metadata, so the
metadata keeps the length it had and every absolute offset in `iloc` still
points where it pointed. What changes is one row or column of picture coming
back, which is the row that was always there.

  scripts/avif-drop-clap.py public/logo-800.avif ...

Prints a line per file and leaves one alone if it carries no clean aperture, so
it is safe to run over a whole directory and safe to run twice.
"""

import struct
import sys

FULL_BOX_META = {'meta'}


def read_boxes(data, start, end):
    """Yields (type, offset, size, header_size) for each box in [start, end)."""
    off = start
    while off + 8 <= end:
        size = struct.unpack('>I', data[off:off + 4])[0]
        btype = data[off + 4:off + 8].decode('latin-1')
        header = 8
        if size == 1:
            size = struct.unpack('>Q', data[off + 8:off + 16])[0]
            header = 16
        elif size == 0:
            size = end - off
        if size < header or off + size > end:
            raise ValueError('malformed box %r at %d' % (btype, off))
        yield btype, off, size, header
        off += size


def find_box(data, start, end, wanted):
    for btype, off, size, header in read_boxes(data, start, end):
        if btype == wanted:
            return off, size, header
    return None


def box(btype, payload):
    return struct.pack('>I', 8 + len(payload)) + btype.encode('latin-1') + payload


def rewrite_ipco(data, off, size, header):
    """Returns (new ipco bytes, old-to-new 1-based index map, dropped indices)."""
    kept = []
    dropped = set()
    index_map = {}
    index = 0
    for btype, boff, bsize, _ in read_boxes(data, off + header, off + size):
        index += 1
        if btype == 'clap':
            dropped.add(index)
            continue
        kept.append(data[boff:boff + bsize])
        index_map[index] = len(kept)
    return box('ipco', b''.join(kept)), index_map, dropped


def rewrite_ipma(data, off, size, header, index_map, dropped):
    version = data[off + header]
    flags = struct.unpack('>I', b'\x00' + data[off + header + 1:off + header + 4])[0]
    wide_ids = version >= 1
    wide_index = bool(flags & 1)
    count = struct.unpack('>I', data[off + header + 4:off + header + 8])[0]
    pos = off + header + 8
    out = bytearray()
    for _ in range(count):
        if wide_ids:
            out += data[pos:pos + 4]
            pos += 4
        else:
            out += data[pos:pos + 2]
            pos += 2
        assoc_count = data[pos]
        pos += 1
        assoc = bytearray()
        kept = 0
        for _ in range(assoc_count):
            if wide_index:
                raw = struct.unpack('>H', data[pos:pos + 2])[0]
                pos += 2
                essential, index = raw >> 15, raw & 0x7FFF
            else:
                raw = data[pos]
                pos += 1
                essential, index = raw >> 7, raw & 0x7F
            if index in dropped:
                continue
            index = index_map.get(index, index)
            kept += 1
            if wide_index:
                assoc += struct.pack('>H', (essential << 15) | index)
            else:
                if index > 0x7F:
                    raise ValueError('property index %d needs a wider ipma' % index)
                assoc += bytes([(essential << 7) | index])
        out += bytes([kept]) + assoc
    payload = data[off + header:off + header + 4] + struct.pack('>I', count) + bytes(out)
    return box('ipma', payload)


def rewrite_iprp(data, off, size, header):
    ipco = find_box(data, off + header, off + size, 'ipco')
    if ipco is None:
        return None
    new_ipco, index_map, dropped = rewrite_ipco(data, *ipco)
    if not dropped:
        return None
    parts = []
    for btype, boff, bsize, bheader in read_boxes(data, off + header, off + size):
        if btype == 'ipco':
            parts.append(new_ipco)
        elif btype == 'ipma':
            parts.append(rewrite_ipma(data, boff, bsize, bheader, index_map, dropped))
        else:
            parts.append(data[boff:boff + bsize])
    return box('iprp', b''.join(parts))


def drop_clap(data):
    """Returns the file with no clean aperture, or None if it had none."""
    meta = find_box(data, 0, len(data), 'meta')
    if meta is None:
        return None
    moff, msize, mheader = meta
    body_start = moff + mheader + (4 if 'meta' in FULL_BOX_META else 0)
    iprp = find_box(data, body_start, moff + msize, 'iprp')
    if iprp is None:
        return None
    new_iprp = rewrite_iprp(data, *iprp)
    if new_iprp is None:
        return None

    parts = []
    for btype, boff, bsize, _ in read_boxes(data, body_start, moff + msize):
        parts.append(new_iprp if btype == 'iprp' else data[boff:boff + bsize])
    body = data[moff + mheader:body_start] + b''.join(parts)

    # The metadata keeps the length it had. Everything after it - the media
    # data, and the absolute offsets in iloc that address it - then needs no
    # adjustment at all, which is the whole reason for the padding.
    slack = (msize - mheader) - len(body)
    if slack < 8:
        raise ValueError('freed %d bytes, too few for the padding box' % slack)
    body += box('free', b'\x00' * (slack - 8))
    new_meta = struct.pack('>I', msize) + b'meta' + body
    if len(new_meta) != msize:
        raise ValueError('metadata changed length')
    return data[:moff] + new_meta + data[moff + msize:]


def main(paths):
    touched = 0
    for path in paths:
        with open(path, 'rb') as handle:
            data = handle.read()
        try:
            out = drop_clap(data)
        except ValueError as error:
            print('%s: %s' % (path, error), file=sys.stderr)
            return 1
        if out is None:
            print('%s: no clean aperture' % path)
            continue
        if len(out) != len(data):
            print('%s: length moved' % path, file=sys.stderr)
            return 1
        with open(path, 'wb') as handle:
            handle.write(out)
        print('%s: clean aperture dropped' % path)
        touched += 1
    print('%d file(s) rewritten' % touched)
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
