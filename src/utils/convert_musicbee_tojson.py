import json

global library


def decode_from_7bit(data):
    """
    Decode 7-bit encoded int from str data
    """
    result = 0
    for index, char in enumerate(data):
        #byte_value = ord(char)
        result |= (char & 0x7f) << (7 * index)
        if char & 0x80 == 0:
            break
    return result


def read_int(bytes_):
    return int.from_bytes(bytes_, byteorder="little", signed=True)


def read_uint(bytes_):
    return int.from_bytes(bytes_, byteorder="little")


def read_str(file):
    len_1 = file.read(1)
    if read_uint(len_1) > 0x7F:
        len_2 = file.read(1)
        if read_uint(len_2) > 0x7F:
            length = decode_from_7bit([read_uint(len_1), read_uint(len_2), read_uint(file.read(1))])
        else:
            length = decode_from_7bit([read_uint(len_1), read_uint(len_2)])
    else:
        length = read_uint(len_1)
    if length == 0:
        return ""
    return file.read(length).decode("utf-8")


with open("E:\\Dropbox\\MUSICA\\MP3\\TANGO\\other_stuff\\MUSICBEE DATABASES\\Eduardo_test\\MusicBeeLibrary.mbl", "rb") as mbl:
    count = read_int(mbl.read(4))

    if not count & 0xFF:
        raise

    count = count >> 8
    library = {"file_count": count, "files": []}

    while True:
        media = {"file_designation": read_uint(mbl.read(1))}
        if media["file_designation"] == 1:
            break

        if 10 > media["file_designation"] > 1:
            media["status"] = read_uint(mbl.read(1))
            if media["status"] > 6:
                raise

            media["unknown_1"] = read_uint(mbl.read(1))
            media["play_count"] = read_uint(mbl.read(2))
            media["date_last_played"] = read_int(mbl.read(8))
            media["skip_count"] = read_uint(mbl.read(2))
            media["file_path"] = read_str(mbl)
            print(media["file_path"])
            if media["file_path"] == "":
                raise

            media["file_size"] = read_int(mbl.read(4))
            media["sample_rate"] = read_int(mbl.read(4))
            media["channel_mode"] = read_uint(mbl.read(1))
            media["bitrate_type"] = read_uint(mbl.read(1))
            media["bitrate"] = read_int(mbl.read(2))
            media["track_length"] = read_int(mbl.read(4))
            media["date_added"] = read_int(mbl.read(8))
            media["date_modified"] = read_int(mbl.read(8))

            media["artwork"] = []
            while True:
                art = {"type": read_uint(mbl.read(1))}
                if art["type"] > 253:
                    break

                art["string_1"] = read_str(mbl)
                art["store_mode"] = read_uint(mbl.read(1))
                art["string_2"] = read_str(mbl)
                media["artwork"].append(art)

            media["tags_type"] = read_uint(mbl.read(1))
            media["tags"] = {}
            while True:
                tag_code = read_uint(mbl.read(1))
                if tag_code == 0:
                    break
                if tag_code == 255:
                    c = read_int(mbl.read(2))
                    i = 0
                    media["cue"] = []

                    while i < c:
                        cue = {}
                        cue["a"] = read_uint(mbl.read(1))
                        cue["b"] = read_uint(mbl.read(2))
                        cue["c"] = read_int(mbl.read(8))
                        cue["d"] = read_uint(mbl.read(2))
                        media["cue"].append(cue)
                        i += 1
                    break

                media["tags"][str(tag_code)] = read_str(mbl)


            library["files"].append(media)
        else:
            raise
    print(count, len(library["files"]))


with open("E:\\Dropbox\\MUSICA\\MP3\\TANGO\\other_stuff\\MUSICBEE DATABASES\\Eduardo_test\\MBL.json", "w") as jfile:
    json.dump(library, jfile, indent=2)
