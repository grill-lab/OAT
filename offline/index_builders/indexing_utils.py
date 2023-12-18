from typing import Callable
import stream
import os
import json
import shutil
from utils import logger


def get_protobuf_list_messages(path, proto_message):
    """Retrieve list of protocol buffer messages from binary file"""
    return [d for d in stream.parse(path, proto_message)]


def write_protobuf_list_to_file(path, protobuf_list, buffer_size=10):
    """Write list of Documents messages to binary file."""
    stream.dump(path, *protobuf_list, buffer_size=buffer_size)


def write_to_file(output_dir, out_path, docs_list):
    # Write to file.
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    with open(out_path, 'w') as f:
        for doc in docs_list:
            if 'text' in doc:
                if len(doc['text']) > 0:
                    f.write(json.dumps(doc) + '\n')
            else:
                f.write(json.dumps(doc) + '\n')


def write_doc_file_from_lucene_indexing(
    input_dir,
    output_dir,
    proto_message,
    build_doc_function: Callable,
    how='all',
    include_proto=False,
    out_files_begin_with='',
    remove_prev=True,
):
    """Write into a folder json documents that represent proto messages."""
    # Get list of files from 'in_directory'.
    try:
        file_names = [f for f in os.listdir(input_dir) if '.bin' in f]
    except FileNotFoundError as fnfe:
        raise Exception(
            f'Indexer input directory "{input_dir}" does not exist. You might need to enable the "TaxonomyBuildRunner" module in config.py'
        ) from fnfe

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    elif remove_prev:
        shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    for file_name in file_names:
        # Build in and out paths for file processing.
        in_path = os.path.join(input_dir, file_name)

        file_name = file_name.split(os.sep)[-1]
        out_path = os.path.join(
            output_dir,
            out_files_begin_with + file_name[: len(file_name) - 4] + '.jsonl',
        )

        # Build list of Pyserini documents.
        proto_list = get_protobuf_list_messages(
            path=in_path, proto_message=proto_message
        )
        logger.info(f'INCLUDE PROTO? {include_proto}')
        docs_list = [
            build_doc_function(proto, include_proto=include_proto)
            for proto in proto_list
        ]

        logger.info(f'out temp path {output_dir}, {out_path}')
        write_to_file(output_dir, out_path, docs_list)


def build_json_docs(
    input_dir,
    output_dir,
    proto_message,
    include_proto,
    build_doc_function: Callable,
    out_files_begin_with='',
    remove_prev=True,
):
    """Build index given directory of files containing taskmaps."""
    # Write Pyserini readable documents (i.e. json) to temporary folder.
    logger.info('IN JSON DOCS')
    logger.info(f'OUT FILES BEGINS WITH {out_files_begin_with}')
    logger.info(f'INCLUDE PROTO {include_proto}')
    logger.info(f'OUTPUT DIR {output_dir}')
    write_doc_file_from_lucene_indexing(
        input_dir=input_dir,
        output_dir=output_dir,
        proto_message=proto_message,
        include_proto=include_proto,
        build_doc_function=build_doc_function,
        out_files_begin_with=out_files_begin_with,
        remove_prev=remove_prev,
    )


def filter_duplicates(input_dir, file_type='.jsonl'):
    """Removes duplicate values prior to indexing for categories."""
    file_names = [f for f in os.listdir(input_dir) if file_type in f]

    unique_el = set()

    for file_name in file_names:
        path = os.path.join(input_dir, file_name)
        with open(path, 'r') as f:
            lines = [json.loads(line) for line in f]

        new_lines = []
        for line in lines:
            if line['contents'] not in unique_el:
                new_lines.append(line)
            unique_el.add(line['contents'])

        with open(path, 'w') as f:
            for line in new_lines:
                f.write(json.dumps(line))
