#!/bin/sh

ls /shared/protobufs | \
grep .proto | \
xargs python3 -m grpc_tools.protoc \
          --proto_path=/shared/protobufs/ \
          --python_out=/shared/compiled_protobufs \
          --grpc_python_out=/shared/compiled_protobufs

echo "Built Services and TaskMap protobufs"