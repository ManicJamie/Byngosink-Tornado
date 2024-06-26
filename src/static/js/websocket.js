const websocket = new ReconnectingWebSocket(
    (window.location.pathname.replace("board", "").replace(/\/+$/, "") + "/ws")
);

function handleMessage(event) {
    const data = JSON.parse(event.data);
    if (data.verb == "SYNC") {
        handleSync(data);
    } else {
        window.dispatchEvent(new CustomEvent("ERROR", {detail: `Unknown verb received: Message ${data}`}));
    }
}

function send(object) {
    console.debug("sending" + JSON.stringify(object));
    websocket.send(JSON.stringify(object));
}

function handleSync(data) {
    if ("CLEAR" in data && data.CLEAR) {
        window.dispatchEvent(new CustomEvent("CLEAR"));
    }
    if ("teams" in data) {
        window.dispatchEvent(new CustomEvent("TEAMS", { detail: data.teams })); // dict[int, team]
    }
    if ("goals" in data) {
        console.debug(data.goals);
        window.dispatchEvent(new CustomEvent("GOALS", { detail: data.goals })); // dict[int, goal]
    }
    if ("marks" in data) {
        console.debug(data.marks);
        window.dispatchEvent(new CustomEvent("MARKS", { detail: data.marks })); // dict[int, teamId]
    }
    // if ("chat" in data) {
    //     window.dispatchEvent(new CustomEvent("CHAT", { marks: data.chat }));
    // }

    SYNCED(data.id);
}

function SYNCED(id) {
    send({
        verb: "SYNCED",
        id: id,
    });
}

function MARK(index, mark) {
    send({
        verb: "MARK",
        index: index,
        mark: mark,
    });
}

function CREATE_TEAM(name, colour) {
    send({
        verb: "CREATE_TEAM",
        name: name,
        colour: colour,
    });
}

function JOIN_TEAM(uuid) {
    send({
        verb: "JOIN_TEAM",
        uuid: uuid,
    });
}

function subscribeWebsocket() {
    websocket.addEventListener("message", (data) => handleMessage(data));
    websocket.addEventListener("error", (event) => console.error(event));
}

window.addEventListener("DOMContentLoaded", subscribeWebsocket);
