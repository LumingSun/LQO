import shutil
import random
import sys
import yaml
from database_env import *
from algorithm.neo import *
from model import *

SEED = 123

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)


if __name__ == '__main__':
    mp.set_start_method("spawn")
    np.random.seed(123)
    torch.manual_seed(123)

    config_path = sys.argv[1]
    env_config_path = sys.argv[2]
    with open(config_path, 'r') as file:
        d = yaml.load(file, Loader=yaml.FullLoader)
    with open(env_config_path, "r") as f:
        env_config = json.load(f)
    Path(d['neo_args']['logdir']).mkdir(parents=True, exist_ok=True)
    shutil.copy(config_path, Path(d['neo_args']['logdir']) / 'config.yaml')
    env_config['return_latency'] = d['neo_args']['latency']

    test_set = env_config['test_queries']
    print(test_set)
    env_config['db_data'] = {
        k: v for k, v in env_config['db_data'].items() if not k in test_set}

    # create_agent
    agent = Agent(TransformerNet(**d['net_args']), collate_fn=collate,
                  device=d['neo_args']['device'])

    # load initial experience
    experience = []
    env = DataBaseEnv(env_config)

    # also optimizer plans
    path_plan = Path(d['neo_args']['baseline_path'])
    baseline_plans = {}
    for p in path_plan.glob("*.sql.json"):
        print(p)
        query = p.parts[-1][:-5]
        if query in test_set:
            continue
        plan = Plan()
        plan.load(p)
        env.plan = plan
        cost = env.reward()
        experience.append([env.plan, cost, query])
        baseline_plans[query] = env.plan

    print('latency: ',  d['neo_args']['latency'] == True)

    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)
    alg = Neo(agent, env_config, d['neo_args'],
              d['train_args'], experience, baseline_plans)
    alg.run()
