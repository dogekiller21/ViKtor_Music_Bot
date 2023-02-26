`apt install libffi-dev libnacl-dev python3-dev`

>In case to resolve **requirements conflict**:
>* Comment `vkwave` from `requirements.txt`
>* Install all other packages (e.g `pip install -r requirements.txt`)
>* Install `vkwave` (e.g `pip install vkwave`)
>* Install `typing_extensions==4.5.0` (e.g `pip install --upgrade typing_extensions==4.5.0`)