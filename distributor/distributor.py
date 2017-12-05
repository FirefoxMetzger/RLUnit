import heapq
import os
import itertools
from tempfile import gettempdir
import urllib.request
from flask import Flask, request, jsonify
from flask_restful import Resource, Api
import importlib
import json
from pathlib import Path
import sys

# inspired by:
# https://docs.python.org/3/library/heapq.html
class Queue(object):
    def __init__(self):
        self.queue = []
        self.entry_map = {}
        self.removed = "<removed-element>"
        self.counter = itertools.count() #unique counter

    def add_trial(self, trial_data, priority=0):
        trial_idx, agent_name, _ = trial_data
        if (trial_idx, agent_name) in self.entry_map:
            self.remove_trial(trial_idx, agent_name)
        count = next(self.counter)
        entry = [priority, count, trial_data]
        self.entry_map[(trial_idx, agent_name)] = entry
        heapq.heappush(self.queue, entry)

    def remove_trial(self, trial_idx, agent_name):
        entry = self.entry_map.pop((trial_idx, agent_name))
        entry[-1] = self.removed

    def pop(self):
        while self.queue:
            priority, count, trial = heapq.heappop(self.queue)
            if trial is not self.removed:
                trial_idx, agent_name, _ = trial
                del self.entry_map[(trial_idx, agent_name)]
                return trial
        raise KeyError("pop from empty queue")

task_queue = Queue()
known_agents = dict()
currently_processed = dict()
tmp_location = Path(gettempdir())/'RLUnit_distributor'
os.makedirs(tmp_location, exist_ok=True)

class Trial(Resource):
    def get(self, agent_name, trial_idx):
        if agent_name not in known_agents:
            return "Unknown Agent"

        num_trials = known_agents[agent_name]["num_trials"]
        if trial_idx < 0 or trial_idx >= num_trials:
            return ("%s only has %d trials. Requested trial %s" %
                        (agent_name, num_trials, trial_idx))

        idx = (trial_idx, agent_name)
        if idx in task_queue.entry_map:
            status = "waiting"
        elif idx in currently_processed:
            status = "being processed"
        else:
            status = "done"
            
        spec = {
            "status": status
            }
        return json.dumps(spec)
    
    def put(self, agent_name, trial_idx):
        if agent_name not in known_agents:
            return "Unknown Agent"

        num_trials = known_agents[agent_name]["num_trials"]
        if trial_idx < 0 or trial_idx >= num_trials:
            return ("%s only has %d trials. Requested trial %s" %
                        (agent_name, num_trials, trial_idx))

        idx = (trial_idx, agent_name)
        if idx not in task_queue.entry_map:
            return "The trial is already finished or being processed."

        url = known_agents[agent_name]["url"]
        try:
            priority = int(request.form["priority"])
        except KeyError:
            return "Form must send a priority value"
        
        trial_data = (trial_idx, agent_name, url)
        task_queue.add_trial(trial_data,priority)
        return ("%s: Priority of task %d is now %d" %
                    (agent_name, trial_idx, priority))

class Agent(Resource):
    def get(self, agent_name):
        if agent_name not in known_agents:
            return "Unknown Agent"

        trial_status = {
                    "finished":list(),
                    "being_processed":list(),
                    "waiting":list()
                 }

        num_trials = known_agents[agent_name]["num_trials"]
        for trial in range(num_trials):
            idx = (trial, agent_name)
            if idx in task_queue.entry_map:
                trial_status["waiting"].append(trial)
            elif idx in  currently_processed:
                trial_status["being_processed"].append(trial)
            else:
                trial_status["finished"].append(trial)

        spec = known_agents[agent_name].copy()
        spec["trial_status"] = trial_status
            
        return json.dumps(spec)
    
    def put(self, agent_name, priority):
        if agent_name not in known_agents:
            return "Unknown Agent"

        num_updated = 0
        num_trials = known_agents[agent_name]["num_trials"]
        url = known_agents[agent_name]["url"]
        for trial in range(num_trials):
            queue_element = (trial, agent_name)
            # data format inside queue
            trial_data = (trial, agent_name, url)
            if queue_element in task_queue.entry_map:
                task_queue.add_trial(trial_data, priority)
                num_updated = num_updated + 1
        
        return ("Updated %d trials" % num_updated)
    
    def post(self, agent_name):
        """
            Creates a new agent and adds it to the queue for computation.
            If the agent exists already it will be readded and overwritten.
        """
        url = request.form["url"]
        spec = self.get_spec(agent_name, url)
        print(spec, file=sys.__stderr__)
        num_trials = spec["num_trials"]
        agent_name = spec["name"]
        known_agents[agent_name] = spec
        
        for trial in range(num_trials):
            entry = (trial, agent_name, url)
            try:
                priority = spec["priority"][trial]
            except KeyError:
                priority = 100
            task_queue.add_trial(entry, priority)
        
        return ("Added %d trials to the queue" % num_trials)


    def get_spec(self, agent_name, url):
        try: # download the agent
            _, file_name = os.path.split(url)
            tmp_agent = tmp_location / file_name
            urllib.request.urlretrieve(url, tmp_agent)
        except:
            return "Could not download the file for some reason."

        spec = importlib.util.spec_from_file_location("agent", tmp_agent)
        agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent)

        if "num_trials" not in agent.spec:
            agent.spec["num_trials"] = 1
        num_trials = agent.spec["num_trials"]

        agent.spec["url"] = url
        agent.spec["name"] = agent_name
        return agent.spec

class TrialQueue(Resource):
    def get(self):
        trials = []
        for priority, _, trial_data in task_queue.queue:
            if trial_data is not task_queue.removed:
                trial_idx, agent_name, url = trial_data
                trials.append((priority, trial_idx, agent_name, url))
        return json.dumps(trials)

class NextTask(Resource):
    def get(self):
        try:
            priority, _, trial_data = task_queue.queue[0]
        except IndexError:
            return "The queue is empty"
        return json.dumps((priority, *trial_data))

    def post(self):
        try:
            trial_data = task_queue.pop()
        except KeyError:
            trial_data = (0,'no work', '')
        return jsonify(trial_data)

app = Flask(__name__)
api = Api(app)

api.add_resource(Agent,
                        "/agent/<string:agent_name>",
                        "/agent/<string:agent_name>/<int:priority>")
api.add_resource(TrialQueue, "/queue/list")
api.add_resource(NextTask, "/queue/next")
api.add_resource(Trial, "/trial/<string:agent_name>/<int:trial_idx>")

if __name__ == "__main__":
    app.run(host="0.0.0.0")
