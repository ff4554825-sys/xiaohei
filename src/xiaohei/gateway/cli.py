from typing import Dict, Any, Optional
from loguru import logger
import asyncio
import cmd
import sys

from ..types import Task, TaskType
from ..cognition import TaskParser, Planner, Critic, ControlDecider
from ..execution import Executor


class CLI(cmd.Cmd):
    intro = "XiaoHei Agent OS CLI - Type 'help' for commands\n"
    prompt = "xiaohei> "

    def __init__(self, task_parser=None, planner=None, executor=None, critic=None, control_decider=None):
        super().__init__()
        self._task_parser = task_parser or TaskParser()
        self._planner = planner or Planner()
        self._executor = executor or Executor()
        self._critic = critic or Critic()
        self._control_decider = control_decider or ControlDecider()
        self._current_task = None
        logger.info("CLI initialized")

    def do_run(self, arg):
        """Run a task: run <task input>"""
        if not arg:
            print("Usage: run <task input>")
            return

        try:
            self._current_task = self._task_parser.parse(arg)
            print(f"Task parsed: {self._current_task.type.value} (ID: {self._current_task.id})")

            plans = self._planner.diverge(self._current_task)
            print(f"Generated {len(plans)} plan(s)")

            scored_plans = self._planner.score(plans, self._current_task)
            selected_plan = self._planner.select(scored_plans)

            if selected_plan:
                print(f"Selected plan with score: {selected_plan.total_score:.2f}")
                for i, step in enumerate(selected_plan.plan, 1):
                    print(f"  {i}. {step}")

                steps = self._executor.decompose(self._current_task)
                result = asyncio.run(self._executor.execute(self._current_task, steps))

                print(f"\nExecution result: {'Success' if result.success else 'Failed'}")
                if result.success:
                    print(f"Output: {result.output}")
                else:
                    print(f"Error: {result.error}")

                review = self._critic.review(self._current_task, {"success": result.success, "output": result.output})
                print(f"\nCritic review:")
                print(f"  Alignment: {review['alignment']:.2f}")
                print(f"  Correctness: {review['correctness']:.2f}")
                print(f"  Completeness: {review['completeness']:.2f}")
                print(f"  Safety: {review['safety']:.2f}")

                decision = self._control_decider.decide(self._current_task, review)
                print(f"\nDecision: {decision.type.value} - {decision.reason}")

        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"CLI execution error: {e}")

    def do_status(self, arg):
        """Show system status"""
        print("System Status:")
        print("  - Task Parser: Ready")
        print("  - Planner: Ready")
        print("  - Executor: Ready")
        print("  - Critic: Ready")
        print("  - Control Decider: Ready")
        if self._current_task:
            print(f"  - Current Task: {self._current_task.id}")

    def do_clear(self, arg):
        """Clear the screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')

    def do_quit(self, arg):
        """Exit the CLI"""
        print("Exiting XiaoHei CLI...")
        logger.info("CLI exiting")
        sys.exit(0)

    def do_exit(self, arg):
        """Exit the CLI (alias for quit)"""
        self.do_quit(arg)

    def default(self, line):
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands")


def main():
    cli = CLI()
    cli.cmdloop()


if __name__ == "__main__":
    main()
