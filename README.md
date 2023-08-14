# tap-wikipedia

Singer tap for extracting Wikipedia pages.

## One-time setup

    script/bootstrap

## Run tests
    
    script/test

## Extract Wikipedia data 

    poetry run tap-wikipedia --config config/wikipedia.config.json >output/wikipedia.output.jsonl
