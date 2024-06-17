function fillGenerators() {
    let el = document.getElementById("game");
    el = el.options[el.selectedIndex];
    let generators = JSON.parse(el.getAttribute("data-gens"));
    let target = document.getElementById("generator");
    let options = [];
    generators.forEach((gen) => {
        options.push(new Option(gen, gen));
    });
    target.replaceChildren(...options);
}

function fillBoardMeta() {
    console.log("running");
    let el = document.getElementById("board");
    el = el.options[el.selectedIndex];
    let metas = JSON.parse(el.getAttribute("data-meta"));
    let target = document.getElementById("board_meta");
    let fields = [];
    metas.forEach((meta) => {
        f = document.createElement("div");
        f.classList.add("flex", "fill");
        let l = document.createElement("l");
        l.textContent = meta;
        let i = document.createElement("input");
        i.type = "number"; // TODO: derive from data
        i.name = meta;
        i.classList.add("creation-width", "rounded");
        f.replaceChildren(l, i);
        fields.push(f);
    });
    target.replaceChildren(...fields);
}

window.addEventListener("DOMContentLoaded", () => {
    fillGenerators();
    fillBoardMeta();
});
