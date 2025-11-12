# 


## Setup

General setup you can just run `uv sync` and it will install all required packages. You can see the once being installed and used in  `pyproject.toml` under dependencies.



## For AWS Pipeline

set local ENV variables:
```sh
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
```

Note: You can also set them in [secrets.toml][.dlt/secrets.toml] directly - I have set above and in [.env](.env) it will source them automatically with dlt feature of `SOURCES__FILESYSTEM__CREDENTIALS__AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"` as example.
