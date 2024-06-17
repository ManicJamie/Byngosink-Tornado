# Byngosink

A goal-syncing application inspired by [Bingosync](https://bingosync.com) that adds arbitrary board sizes, hidden goals (such as in Exploration game modes), and custom colours.

## Board Types

- ### Non-Lockout / Lockout

    Familiar to Bingosync users; all goals are visible & can be marked at any time. Lockout rules means once a team marks a goal, other teams cannot mark that goal. Suitable for many formats.

- ### Exploration

    Hidden goal format; You start with the middle goal revealed, marking a goal reveals the 4 adjacent goals. Goal is to reach any corner (or multiple).

- ### Get To The Other Side

    Hidden goal format like Exploration, but you start with all Column 1 goals revealed. Goal is to mark 1 goal in the furthest column.

## Generators

Byngosink provides a few default generator types, accessible under the `Custom` game. You can add your game's generators in [src/generators/jsons](./src/generators/jsons).

- BasicGenerator

    A simplistic generator with no line balancing. Supports goal exclusions, tiebreaker goals, weighting, and maximum cost guarantees. Used as a fallback if other generators fail to produce a result.

- SynerGen

    Based on Bingosync's `synerGen.js`, ...

- SRLv5

    Similar but not identical to SRLv5.

## Stack

Byngosink is run on a sole Tornado web server using Tortoise ORM. Using Tornado to serve the site as well as the WebSocket allows a deep connection between SSG and live WebSocket communications.

Once connected to a room, client actions are triggered by messages over the WebSocket. The server will send out SYNC messages as appropriate to inform the client to update their display. The client responds with SYNCED and the ID of the SYNC message to keep the server informed of all missing data.
