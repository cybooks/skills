# Schemas

The four `.xsd` files in this folder are the XML schemas the Cyprus Tax
Department publishes for files uploaded to its portal. They are here
unchanged, so the script can test a file against them before it is written.

| File | What it describes |
|---|---|
| `cy-f4-2010-declaration.xsd` | The VAT return |
| `cy-vies1-2010-declaration.xsd` | The monthly VIES statement |
| `cy-core.xsd`, `olive-core.xsd` | Types the two schemas above use |

They are the work of the Ministry of Finance of the Republic of Cyprus and
its contractors. The Tax Department publishes them with its instructions
for building these files (as `xsd-fpa-ext.zip`), and each schema states
that it is intended for public use. That statement is not a licence. The
MIT licence of this skill covers the skill's own text and code, not these
four files.

If the Tax Department publishes a newer version, replace the files here
with it. The script reads whatever is in this folder.
