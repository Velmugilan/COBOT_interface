import React, { useState } from 'react';

interface Waypoint {
  id: number;
  type: 'JOINT' | 'CARTESIAN';
  data: Record<string, number> | { axis: string, distance: number };
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
        } else {
          res = await fetch(`http://${window.location.hostname}:8000/api/motion/cartesian`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(wp.data)
          });
        }
        
        const data = await res.json();
        if (!data.success) {
          setResultMsg(`Failed at step ${i + 1}: ${data.message}`);
          setRunning(false);
          return;
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
      
      <div className="flex space-x-4 mb-4">
        <button 
          onClick={addJointWaypoint}
          disabled={running}
          className="bg-purple-600 hover:bg-purple-500 px-4 py-2 rounded text-sm font-bold shadow transition-colors"
        >
          + Record Current Joint Pose
        </button>
        <button 
          onClick={() => addCartesianWaypoint('z', -0.1)}
          disabled={running}
          className="bg-teal-600 hover:bg-teal-500 px-4 py-2 rounded text-sm font-bold shadow transition-colors"
        >
          + Add Relative Z Move (Down)
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
                  {wp.type === 'JOINT' 
                    ? `JOINT TARGET (${Object.keys(wp.data).length} joints)` 
                    : `CARTESIAN RELATIVE (Axis: ${(wp.data as any).axis}, Dist: ${(wp.data as any).distance})`}
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
