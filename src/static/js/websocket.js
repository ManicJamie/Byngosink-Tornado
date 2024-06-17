const websocket = new ReconnectingWebSocket((window.location.href + "/ws").replace("board/", ""));

function handleMessage(data) {
    const event = JSON.parse(data);
    console.debug(event);
    if (event.verb == "SYNC") {
        handleSync(data);
    } else {
        window.dispatchEvent(new CustomEvent(event.verb, { detail: event.data }));
    }
}

function send(object) {
    console.debug("sending" + JSON.stringify(object));
    websocket.send(JSON.stringify(object));
}

function handleSync(data) {
    if ("teams" in data) {
        window.dispatchEvent(new CustomEvent("TEAMS", { marks: data.teams })); // dict[int, team]
    } else if ("goals" in data) {
        window.dispatchEvent(new CustomEvent("GOALS", { marks: data.goals })); // dict[int, goal]
    } else if ("marks" in data) {
        window.dispatchEvent(new CustomEvent("MARKS", { marks: data.marks })); // dict[int, teamId]
    } else if ("chat" in data) {
        // window.dispatchEvent(new CustomEvent("MARKS", { marks: data.marks }));
    }

    SYNCED(data.id);
}

function SYNCED(id) {
    websocket.send(
        JSON.stringify({
            verb: "SYNCED",
            id: id,
        })
    );
}

function MARK(index, mark) {
    websocket.send(
        JSON.stringify({
            verb: "MARK",
            index: index,
            mark: mark,
        })
    );
}

function CREATE_TEAM(name, colour) {
    websocket.send(
        JSON.stringify({
            verb: "CREATE_TEAM",
            name: name,
            colour: colour,
        })
    );
}

function subscribeWebsocket() {
    websocket.addEventListener("message", ({ data }) => handleMessage(data));
    websocket.addEventListener("error", (event) => console.error(event));
}
