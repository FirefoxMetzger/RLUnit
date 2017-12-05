# RLUnit
A lightweight framework for paralell computation of trials in reinforcement learning using docker swarm.

## Installation
You can run RLUnit on any docker swarm:

    curl https://github.com/FirefoxMetzger/RLUnit/RLUnit.yml | docker stack deploy -c - RLUnit
    
It listens to requests on `Port 5000` and serves the resulting data on `Port 5003`. 

__Note:__ You can always launch a single node swarm locally via: `docker swarm init`

## Example
To add a the [`example_agent`](https://gist.github.com/FirefoxMetzger/e2a42002b2f21ebb9c539b5edd3f275b/) (from a GitHub gist) use RLUnit's REST API and pass it the raw location:

    curl -d "url=https://gist.githubusercontent.com/FirefoxMetzger/e2a42002b2f21ebb9c539b5edd3f275b/raw/fb646bd574b597ede4bd127419909b5bf42bed2d/Qlearning_example.py" -X POST http://127.0.0.1:5000/agent/example_agent

This assumes that the RLUnit runs at `127.0.0.1`. After computation you can collect the results

    curl -X GET http://127.0.0.1:5003/results/agent/example_agent > example_agent.zip

If you are impatient, you can check the current task queue to see what is still pending

    curl -X GET localhost:5000/queue/list

It is worth noting that the `example_agent` can be run on it's own and does not require RLUnit to work. This is very useful for both, rapidly iterating over the agent's code and sharing it with others.

### Spec dict
RLUnit looks for a variable called `spec` in the agent's namespace. It is a dictionary with the following structure:

    spec = {
        "num_trials":10,
        "saved_files":["episode.npy"], # files contained in the results.zip
        "trial_func":"run_trial" # the function that runs a single trial
    }
    
### Trial func
The agent's `trial_func` is called for each trial. As the name implies it is expected that this function calculates a single trial. The precise name can be modified via the `spec`. If not found it defaults to `run_trial(trial_index)` and falls back to `main`, if neither `spec["trial_func"]` nor `<module>.run_trial(trial_index)` are defined.

RLUnit passes a single integer `trial_index` to the function, which should be used to set trial specific initialization, e.g. random seeds, learning rates or other hyper-parameters for the trial. See the [`example_agent`](https://gist.github.com/FirefoxMetzger/e2a42002b2f21ebb9c539b5edd3f275b/) for more details.