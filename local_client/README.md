# Local client

The local client can be used for development and testing of OAT. It is implemented as a Flask application which by default will be accessible at http://localhost:9000 after starting an OAT deployment.

## Details

There are two Flask endpoints defined in `main.py`. The first handles requests to the base URL and renders the page using Flask's `render_template` method. The second endpoint (`/getresponse`) is triggered by the `call` method in `scripts.js`, and is responsible for sending the current input to OAT before receiving and displaying the system response. The address to send the requests to is defined by the `DISTRIBUTOR_URL` environment variable.

The request sent to the orchestrator is an HTTP POST with a JSON payload. The JSON structure is:
```
{
    "text": "user input text",
    "id": "session ID",
    "headless": "false",
}
```

The `id` is randomly generated by `assignID()` in `scripts.js`, which is called by the `onLoad` handler of `chat.html`. All the IDs the local client generates will have a `local_` prefix so they can be distinguished in the sessions database.

The response sent back by OAT is a JSON-serialized `OutputInteraction` proto object (see `shared/protobufs/taskmap.proto`).

## Policy source information

The `OutputInteraction` objects returned by OAT include information about the policy that created them as an aid for debugging and testing. See the `OutputSource` protobuf and `set_source` in `shared/utils/policies.py`.

The local client will display a coloured background for system responses based on the originating policy name. The colours used for this are defined in `style.css`. 

Additonally the message prefix will be set to `BOT[policy_name]`, and clicking the `policy_name` text will display a popup with the filename and line number.
