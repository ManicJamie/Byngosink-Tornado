class CellState {
    goal = "";
    marked = [];
    activeTeamId = null;

    updateGoal(newGoal) {
        if (this.goal != newGoal) {
            this.goal = newGoal;
            return true;
        }
        return false;
    }

    updateMarked(newMarked) {
        if (this.marked !== newMarked) {
            this.marked = newMarked;
            return true;
        }
        return false;
    }

    updateActiveTeamId(newActiveTeamId) {
        if (this.activeTeamId == newActiveTeamId) return false;
        var prevId = this.activeTeamId;
        this.activeTeamId = newActiveTeamId;

        for (var marking of this.marked) {
            if (marking[0] == newActiveTeamId || marking[0] == prevId) return true;
        }
        return false;
    }

    isMarkedFor(teamId) {
        if (teamId == null) return false;
        for (var marking of this.marked) {
            if (marking[0] == teamId) return true;
        }
        return false;
    }

    getColourFor(teamId) {
        for (var marking of this.marked) {
            if (marking[0] == teamId) return marking[1];
        }
        return null;
    }

    isFull() {
        // TODO: Fill the cell if the goal cannot be claimed by anyone else (lockout formats)
        // Otherwise, fill if self is only mark
        if (this.marked.length == 1 && this.marked[0][0] == this.activeTeamId) {
            return true;
        }
        return false;
    }
}

const teamColours = {}
var currentTeamId = null;

// let self_uuid = user.uuid {from SSG}
// let cellStates = [CellState() for i in range(index)] {from SSG}

function handle_mark(index) {
    MARK(index, true);
}

window.addEventListener("TEAMS", (teams) => {
    for (const [tId, t] of Object.entries(teams.detail)) {
        teamColours[tId] = t.colour;
        if (self_uuid in t.users) {
            updateCurrentTeamId(tId);
        }
    }
});

window.addEventListener("GOALS", (goals) => {
    for (const [i, g] of Object.entries(goals.detail)) {
        let e = $(`#cell${i} .bingo-cell-content`);
        e.html(g.name);
        // textFit(e, {alignHoriz: true, detectMultiLine: true, reProcess: false, minFontSize: 8})
    }
});

window.addEventListener("MARKS", (marks) => {
    for (const [tId, tMarks] of Object.entries(marks)) {
        for (const i in tMarks) {
            updateCellMarkings(i, null)
        }
    }
});

// Below is code managing SVG fill states. May be moved elsewhere for clarity.

const hoverPct = 0.5;
const activePct = 0.5;
const activePolygonPct = Math.sqrt(activePct);
const svgXOffset = 4;
const svgYOffset = 0;

function pointPrinter(width, height) {
    function scaler(point) {
        let [x, y] = point;
        return `${x * width},${y * height}`
    }
    return scaler;
}

function getRGB(colour) {
    return [parseInt(colour.substring(1, 3), 16), parseInt(colour.substring(3, 5), 16), parseInt(colour.substring(5, 7), 16)];
}

function interpolate(colour1, colour2, pct) {
    var [r1, g1, b1] = getRGB(colour1);
    var [r2, g2, b2] = getRGB(colour2);
    const r = Math.round(r1 + (r2 - r1) * pct);
    const g = Math.round(g1 + (g2 - g1) * pct);
    const b = Math.round(b1 + (b2 - b1) * pct);
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

const squarePolygon = [[0, 0], [1, 0], [1, 1], [0, 1]];
const activePolygon = [[0, activePolygonPct], [activePolygonPct, 0], [1, 0], [1, 1 - activePolygonPct], [1 - activePolygonPct, 1], [0, 1]];

function renderPolygon(svg, width, height, polygon, colour) {
    let node = create_svg("polygon");
    node.setAttribute('points', polygon.map(pointPrinter(width, height)).join(' '));
    node.style = `fill:${colour};stroke:black;stroke-width:1`;
    svg.appendChild(node);
}

function skew(frac) {
    return Math.pow(frac, areaSkew);
}

function reverseSkew(frac) {
    return 1 - skew(1 - frac);
}

function topLeftPoint(pct) {
    if (pct <= 1) return [0, 1 - pct];
    else return [pct - 1, 0];
}

function bottomRightPoint(pct) {
    if (pct <= 1) return [pct, 1];
    else return [1, 2 - pct];
}

// Given a triangle with sides |size|, |size|, and |size| * sqrt(2), divide it evenly into N sections perpendicular to the hypotenuse.
// Results are coordinates along the hypotenuse, scaled to [0, 2*size]
function splitTriangle(size, sections) {
    let totalArea = size * size / 2.0;
    let share = totalArea / sections;

    let splits = [];
    let currentShare = 0;
    let half = ((sections % 2 == 0) ? (sections - 2) : (sections - 1)) / 2;
    for (i = 0; i < half; i++) {
        currentShare += share;

        // x^2/2 = currentShare; x = sqrt(2 * currentShare)
        // dist = sqrt(2) * x; dist = 2 * sqrt(currentShare)
        splits.push(2 * Math.sqrt(currentShare));
    }

    if (sections % 2 == 0) splits.push(size);
    for (i = 0; i < half; i++) splits.push(2 * size - splits[half - 1 - i]);
    return splits;
}

function computeCrossPolygon(startPct, endPct) {
    const points = []
    if (startPct > 0) {
        points.push(bottomRightPoint(startPct));
        points.push(topLeftPoint(startPct));
    } else {
        points.push([0, 1]);
    }
    if (startPct < 1 && endPct > 1) {
        points.push([0, 0]);
    }
    if (endPct < 2) {
        points.push(topLeftPoint(endPct));
        points.push(bottomRightPoint(endPct));
    } else {
        points.push([1, 0]);
    }
    if (startPct < 1 && endPct > 1) {
        points.push([1, 1]);
    }

    return points;
}

function renderCrossPolygons(svg, width, height, markings, leaveGap) {
    if (markings.length == 0) return;

    let pcts = [];
    if (leaveGap) {
        pcts.push(1 - activePolygonPct);
        for (var split of splitTriangle(activePolygonPct, markings.length)) {
            pcts.push(1 - activePolygonPct + split);
        }
        pcts.push(1 + activePolygonPct);
    } else {
        pcts.push(0);
        pcts.push(...splitTriangle(1, markings.length));
        pcts.push(2);
    }

    console.debug("pcts: " + pcts + "; " + markings.length);
    for (i = 0; i + 1 < pcts.length; i++) {
        let polygon = computeCrossPolygon(pcts[i], pcts[i + 1]);
        renderPolygon(svg, width, height, polygon, markings[i][1]);
    }
}

function buildSvgShapes(cell, svg, state) {
    if (state.marked.length == 1 && state.isFull()) {
       renderPolygon(svg, 100, 100, squarePolygon, state.marked[0][1]);
       return;
    }

    if (!state.isFull() || state.isMarkedFor(currentTeamId)) {
        let filtered = [];
        for (var marking of state.marked) {
            if (marking[0] != currentTeamId) {
                filtered.push(marking);
            }
        }
        renderCrossPolygons(svg, 100, 100, filtered, true);
        renderPolygon(svg, 100, 100, activePolygon, state.isMarkedFor(currentTeamId) ? state.getColourFor(currentTeamId) : cellBgColor);
    } else {
        renderCrossPolygons(svg, 100, 100, state.marked, false);
    }
}

function updateCellMarkings(index, teamMarkings) {
    if (index == -1) return;

    const cell = document.getElementById("cell" + index);
    let updated = false;

    let state = cellStates[index];
    if (teamMarkings != null && state.updateMarked(teamMarkings)) updated = true;
    if (state.updateActiveTeamId(currentTeamId)) updated = true;
    if (!updated) return;

    const svg = document.getElementById("cell-bg" + index);
    svg.replaceChildren([]);
    buildSvgShapes(cell, svg, state);
}

function updateCurrentTeamId(newTeamId) {
    currentTeamId = newTeamId;

    for (const cellId in cellStates) {
        updateCellMarkings(cellId, null);
    }
}