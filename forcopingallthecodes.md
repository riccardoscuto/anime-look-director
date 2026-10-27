for /R %f in (*.py *.toml *.md) do @echo. & @echo === FILE: %f === & @type "%f") | clip

