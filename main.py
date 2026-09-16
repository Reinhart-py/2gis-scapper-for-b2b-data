import sys
from gmaps.runner import GMapsRunner
from runner import Runner as TwoGISRunner
from utils.cli_parser import initiate_cli_parser


def main() -> None:
    try:
        config = initiate_cli_parser()
        if config.engine == "2gis":
            # Map parameters for 2GIS runner
            config.start_page = config.start_step
            runner = TwoGISRunner(config=config)
            runner.run()
        elif config.engine == "gmaps":
            runner = GMapsRunner(
                target_input=config.target,
                output_path=config.output_path,
                start_index=config.start_step,
                target_count=config.target_count,
            )
            runner.run()
    except KeyboardInterrupt:
        print("\nProcess terminated gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
