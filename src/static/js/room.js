var alertPlaceholder = null;

const knownTeams = {}; // teamId: {name, members}

function submit_team(event) {
    event.preventDefault();
    CREATE_TEAM($("#inputTeamName").val(), $("#inputTeamColour").val());
    $("#teamCreateModal").modal("hide");
    return false;
}

function handle_error(message) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = [
        `<div class="alert alert-danger alert-dismissible fade show mt-0 mb-2 flex flex-nowrap justify-content-start" role="alert">`,
        `<svg class="bi flex-shrink-0 my-auto" width="24" height="24" role="img" aria-label="Error:"><use xlink:href="#exclamation-triangle-fill"/></svg>`,
        `<div class="">${message}</div>`,
        `<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`,
        `</div>`,
    ].join("");

    document.getElementById("errorAlertPlaceholder").replaceChildren(wrapper);
}

function team_card(id, name, colour, users) {
    const card = document.createElement("div");
    card.setAttribute("data-team", id);
    card.setAttribute("ondblclick", `JOIN_TEAM("${id}")`)
    card.className = "card bg-transparent text-light me-1 mb-1 user-select-none";
    let els = `<div class="card-header px-1 py-0 pointer pe-none" style="background-color: ${colour}">${name}</div>` +
        `<div class="card-body px-1 py-0 pe-none">`

    for (let username of users) {
        els += `<div class="card-text pe-none">${username}</div>`
    }
    els += `</div>`

    card.innerHTML = els;
    return card
}

function respell_teams() {
    let cards = [];
    for (const [tId, t] of Object.entries(knownTeams)) {
        cards.push(team_card(tId, t.name, t.colour, t.users))
    }
    document.getElementById("teamSelector-inner").replaceChildren(...cards)
}

function exit() {}

// Listeners

$("#teamModal").on("shown.bs.modal", function () {
    $("#inputTeamName").trigger("focus");
});

window.addEventListener("DOMContentLoaded", () => {
    $(".colour-wrapper").colorpicker({
        popover: false,
        inline: true,
        container: true,
        format: "hex",
        useAlpha: false,
        fallbackColor: "#ff0000",
        customClass: "bg-light mx-auto",
    });
});

// Websocket listeners

window.addEventListener("CLEAR", () => {
    // Board has been regenerated; refresh ./board
    $("#board-iframe").src += "";
});

window.addEventListener("TEAMS", (teams) => {
    for (const [tId, t] of Object.entries(teams.detail)) {
        knownTeams[tId] = {
            name: t.name,
            colour: t.colour,
            users: t.users,
        };
    }

    respell_teams();
});

window.addEventListener("CHAT", (messages) => {
    console.debug(`Chat: ${messages}`);
});
