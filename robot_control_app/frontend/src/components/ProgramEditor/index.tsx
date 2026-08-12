import React, { useState } from 'react';

interface Waypoint {
  id: number;
  type: 'JOINT' | 'CARTESIAN' | 'GRIPPER_OPEN' | 'GRIPPER_CLOSE';
  data?: Record<string, number> | { axis: string, distance: number };
}

const ProgramEditor = ({ currentJoints }: { currentJoints: Record<string, number> }) => {
  const [program, setProgram] = useState<Waypoint[]>([]);
  const [running, setRunning] = useState(false);
  const [resultMsg, setResultMsg] = useState("");

  const addJointWaypoint = () => {
    setProgram([...program, {
      id: Date.now(),
      type: 'JOINT',
      data: { ...currentJoints }
    }]);
  };

  const addCartesianWaypoint = (axis: string, distance: number) => {
    setProgram([...program, {
      id: Date.now(),
      type: 'CARTESIAN',
      data: { axis, distance }
    }]);
  };

  const addGripperWaypoint = (isOpen: boolean) => {
    setProgram([...program, {
      id: Date.now(),
      type: isOpen ? 'GRIPPER_OPEN' : 'GRIPPER_CLOSE',
    }]);
  };

  const loadDemoPickAndPlace = () => {
    // 1: Move to Pre-Pick, 2: Open, 3: Down, 4: Close, 5: Up, 6: Place, 7: Down, 8: Open, 9: Up
    setProgram([
      { id: Date.now() + 1, type: 'JOINT', data: {'joint_1': 0.0, 'joint_2': -0.78, 'joint_3': 1.57, 'joint_4': -0.78, 'joint_5': -1.57, 'joint_6': 0.0} },
      { id: Date.now() + 2, type: 'GRIPPER_OPEN' },
      { id: Date.now() + 3, type: 'CARTESIAN', data: { axis: 'z', distance: -0.15 } },
      { id: Date.now() + 4, type: 'GRIPPER_CLOSE' },
      { id: Date.now() + 5, type: 'CARTESIAN', data: { axis: 'z', distance: 0.2 } },
      { id: Date.now() + 6, type: 'JOINT', data: {'joint_1': 1.57, 'joint_2': -0.78, 'joint_3': 1.57, 'joint_4': -0.78, 'joint_5': -1.57, 'joint_6': 0.0} },
      { id: Date.now() + 7, type: 'CARTESIAN', data: { axis: 'z', distance: -0.15 } },
      { id: Date.now() + 8, type: 'GRIPPER_OPEN' },
      { id: Date.now() + 9, type: 'CARTESIAN', data: { axis: 'z', distance: 0.2 } },
    ]);
  };

  const removeWaypoint = (id: number) => {
    setProgram(program.filter(w => w.id !== id));
  };

  const runProgram = async () => {
    if (program.length === 0) return;
    setRunning(true);
    setResultMsg("Running sequence...");
    
    for (let i = 0; i < program.length; i++) {
      const wp = program[i];
      try {
        setResultMsg(`Executing Step ${i + 1}/${program.length}...`);
        
        let res;
        if (wp.type === 'JOINT') {
          res = await fetch(`http://${window.location.hostname}:8000/api/motion/joint`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ joints: wp.data })
          });
        } else if (wp.type === 'CARTESIAN') {
          res = await fetch(`http://${window.location.hostname}:8000/api/motion/cartesian`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(wp.data)
          });
        } else if (wp.type === 'GRIPPER_OPEN') {
          res = await fetch(`http://${window.location.hostname}:8000/api/gripper/open`, { method: "POST" });
        } else if (wp.type === 'GRIPPER_CLOSE') {
          res = await fetch(`http://${window.location.hostname}:8000/api/gripper/close`, { method: "POST" });
        }
        
        if (res) {
          const data = await res.json();
          if (!data.success) {
            setResultMsg(`Failed at step ${i + 1}: ${data.message}`);
            setRunning(false);
            return;
          }
        }
      } catch (e: any) {
        setResultMsg(`Error at step ${i + 1}: ${e.message}`);
        setRunning(false);
        return;
      }
    }
    
    setResultMsg("Program Completed Successfully!");
    setRunning(false);
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700 h-full flex flex-col">
      <h2 className="text-lg font-bold mb-4 border-b border-gray-700 pb-2 flex justify-between">
        <span>Task Program Editor</span>
        <span className={resultMsg.includes("Success") ? "text-green-500" : "text-yellow-500"}>{resultMsg}</span>
      </h2>
      
      <div className="flex flex-wrap gap-2 mb-4">
        <button 
          onClick={addJointWaypoint}
          disabled={running}
          className="bg-purple-600 hover:bg-purple-500 px-3 py-1.5 rounded text-xs font-bold shadow transition-colors"
        >
          + Record Joint Pose
        </button>
        <button 
          onClick={() => addCartesianWaypoint('z', -0.1)}
          disabled={running}
          className="bg-teal-600 hover:bg-teal-500 px-3 py-1.5 rounded text-xs font-bold shadow transition-colors"
        >
          + Add Relative Z Down
        </button>
        <button 
          onClick={() => addGripperWaypoint(true)}
          disabled={running}
          className="bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded text-xs font-bold shadow transition-colors"
        >
          + Open Gripper
        </button>
        <button 
          onClick={() => addGripperWaypoint(false)}
          disabled={running}
          className="bg-amber-600 hover:bg-amber-500 px-3 py-1.5 rounded text-xs font-bold shadow transition-colors"
        >
          + Close Gripper
        </button>
        <button 
          onClick={loadDemoPickAndPlace}
          disabled={running}
          className="bg-gray-600 hover:bg-gray-500 px-3 py-1.5 rounded text-xs font-bold shadow transition-colors ml-auto"
        >
          Load Demo Pick & Place
        </button>
      </div>

      <div className="flex-1 bg-gray-900 rounded border border-gray-700 overflow-y-auto p-4 space-y-2">
        {program.length === 0 ? (
          <div className="text-gray-500 italic text-center py-8">No waypoints recorded. Move the robot and add waypoints to build a sequence.</div>
        ) : (
          program.map((wp, idx) => (
            <div key={wp.id} className="flex justify-between items-center bg-gray-800 p-3 rounded shadow-sm border-l-4 border-purple-500">
              <div>
                <span className="font-bold text-gray-300 mr-4">#{idx + 1}</span>
                <span className="text-sm font-mono text-gray-400">
                  {wp.type === 'JOINT' && `JOINT TARGET (${Object.keys(wp.data || {}).length} joints)`}
                  {wp.type === 'CARTESIAN' && `CARTESIAN RELATIVE (Axis: ${(wp.data as any)?.axis}, Dist: ${(wp.data as any)?.distance})`}
                  {wp.type === 'GRIPPER_OPEN' && `ACTION: OPEN GRIPPER`}
                  {wp.type === 'GRIPPER_CLOSE' && `ACTION: CLOSE GRIPPER`}
                </span>
              </div>
              <button 
                onClick={() => removeWaypoint(wp.id)}
                disabled={running}
                className="text-red-400 hover:text-red-300 px-2"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-700 flex justify-between">
        <button 
          onClick={() => setProgram([])}
          disabled={running || program.length === 0}
          className="bg-gray-700 hover:bg-red-600 px-4 py-2 rounded font-bold transition-colors"
        >
          Clear Program
        </button>
        
        <button 
          onClick={runProgram}
          disabled={running || program.length === 0}
          className={`${running ? 'bg-green-800 text-gray-400' : 'bg-green-600 hover:bg-green-500'} px-8 py-2 rounded font-bold transition-colors shadow-lg`}
        >
          {running ? 'EXECUTING PROGRAM...' : '▶ RUN PROGRAM'}
        </button>
      </div>
    </div>
  );
};

export default ProgramEditor;
