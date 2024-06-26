const teamColours = {}

function handle_mark(index) {
    MARK(index, true);
}

window.addEventListener("TEAMS", (teams) => {
    for (const [tId, t] of Object.entries(teams.detail)) {
        teamColours[tId] = t.colour;
    }
});

window.addEventListener("GOALS", (goals) => {
    for (const [i, g] of Object.entries(goals.detail)) {
        $(`#cell${i} .bingo-cell-content`).html(g.name);
    }
});

window.addEventListener("MARKS", (marks) => {
    for (const [tId, marks] of Object.entries(marks)) {
        let colour = teamColours[tId];
        
    }
});