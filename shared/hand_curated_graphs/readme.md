# Excalidraw config

Import from the top a local configuration and use the `graph_nodes.excalidrawlib` file provided
It includes the 5 basic nodes and a sample taskgraph


## Generating TaskGraphs

Run the `draw_to_graph.py` script. It will require the dependencies from _task_graphs_ and _taskmap_pb2_.
Once it is started, it will prompt for a JSON String. 
- You will need to select every node that is in you drawing, and use the **Copy** command.
- Comeback to the script and paste.  It should paste a very long Json string inside the command line.
- Press Enter

This line represents the drawing, and the script will parse it to generate the Graph from the Drawing.

Please rename the out.proto to a more significant name.

## Using the generated graph in the system

The system has support for a FixedSearcher system.
It can be configured with a list of proto-files to extract them and present them.

(NOTE: Theme search interferes with the search results, so if you see a different set of results from what you have configured the system, it is probably caused by theme search triggering.)

You can configure as many files in the fixed searcher to be retrieved, but consider that only 12 will be picked up by the system.
Copy each desired proto-file inside `file_system/custom_taskmaps/`.

Enjoy!
