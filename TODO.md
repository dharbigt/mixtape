# BlorfMix

## Development Environment Assumptions

Local (mari) is running macOS and has html DocRoots mounted at: `/Volumes/html/`. The python venv is not for use on mari and is particular to murphy.

Remote (murphy) is running Linux and hosts the (dev) site via apache, so the venv is murphy's. You can test on the dev server murphy via ssh:

- `ssh murphy cd /var/www/html/mixtape.dev.palodes.com && ls`

- DocRoot: /var/www/html/mixtape.dev.palodes.com
- Logs: /var/log/apache2/mixtape.dev.palodes.com_access.log /var/log/apache2/mixtape.dev.palodes.com_error.log


## ToDo

- [ ] `/admin/mixtape/<id>` Adding or reordering tracks resets track numbers (TRCK ID tag)

## Done

- [X] No longer display mixtapes without authentication. Root "/" route without authentication now displays a landing page with button to log in.

- [X] `/` For authenticated users, the mixtapes are displayed here

- [X] `/` For authenticated users, add an option to download the tracks

- [X] `/admin/` Only available to admin users.

- [X] `/admin/` Add a "Back" link before the "Logout" button that leads to `/`.

- [X] `/admin/mixtape/<id>` Add field for sequence before (to the left) of "Title" in playlist.

- [X] `/admin/mixtape/<id>` Add field for sequence before (to the left) of "Title" in playlist.

- [X] `/admin/mixtape/<id>` Allow drag-and-drop reordering of playlist.

- [X] `/admin/mixtape/<id>` Display duration as minutes and seconds (mm:ss "9:99") rather than "999s")

- [X] `/admin/users` Add this route for listing users (admin only)

- [X] `/admin`: Remove heading "Create New Mixtape" and frame around "Create New Mixtape" button, move the button to the left of the other three (Manage Users, Back to Home, Logout) buttons.

- [X] `/`: Remove uppercase greek pi link at the bottom of the page, it is now redundant

- [X] Apply landing page styling to `/admin` and `/admin/mixtape`: Add title and emoji heading, style tables with matching purple header rows, make buttons purple instead of blue.

- [X] `/admin`: Remove "M3U" link from index since that link is on the mixtape page.

- [X] `/admin/mixtape/<id>`: Remove "M3U" link from top of page — remove the entire box and instead have a subheading for the creator just below the heading for the title. No field name required, i.e. "Joe Kreator" not "Creator: Joe Kreator". Genre and Mixtape ID field need not be displayed.

- [X] `/`: On main page mixtape display, the "description: field linefeeds should be honored in the HTML.

- [X] `/`: Shrink the font for "description" field to 10pt
- [X] `/admin/mixtape/<id>` Adding a new track clears the track's ID tags for "Album"
