from sumolib import checkBinary
import os
import sys

def check_and_make_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            print ("Creation of the directory "+str(path)+" failed")

def set_sumo(gui, roadnet, max_steps, port):
    """
    Configure various parameters of SUMO
    """
    # sumo things - we need to import python modules from the $SUMO_HOME/tools directory
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")

    # setting the cmd mode or the visual mode    
    if gui == False:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')
    # setting the cmd command to run sumo at simulation time
    sumo_cmd = [sumoBinary, "-c", os.path.join('net', roadnet, roadnet+'.sumocfg'), "--no-step-log", "true", "--remote-port", str(port), "--waiting-time-memory", str(max_steps)]

    return sumo_cmd

def set_save_path(roadnet,method):
    """
    Create a new save path with an incremental integer, also considering previously created save paths
    """
    save_path = os.path.join(os.getcwd(),'save',roadnet,method,'')
    os.makedirs(os.path.dirname(save_path),exist_ok=True)

    # dir_content = os.listdir(save_path)
    # if dir_content:
    #     previous_versions = [int(name.split("_")[1]) for name in dir_content]
    #     new_version = str(max(previous_versions) + 1)
    # else:
    #     new_version = '1'
    # data_path = os.path.join(save_path,'result_'+new_version,'')
    # os.makedirs(os.path.dirname(data_path),exist_ok=True)
    return save_path