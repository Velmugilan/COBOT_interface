import React, { useState, useEffect, useRef, useCallback } from 'react';

/**
 * RobotViewer3D — Shows a live view of the RViz2 window by polling
 * snapshot frames from the backend at ~7 FPS.
 */
const RobotViewer3D = ({ joints }: { joints: Record<string, number> }) => {
  const [status, setStatus] = useState<'connecting' | 'live' | 'offline'>('connecting');
  const imgRef = useRef<HTMLImageElement>(null);
  const timerRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  const snapshotUrl = `http://${window.location.hostname}:8000/api/rviz/snapshot`;

  const fetchFrame = useCallback(async () => {
    if (!mountedRef.current) return;
    
    try {
      const res = await fetch(snapshotUrl + `?t=${Date.now()}`);
      if (!mountedRef.current) return;
      
      const rvizStatus = res.headers.get('X-Rviz-Status');
      
      if (res.ok) {
        const blob = await res.blob();
        if (!mountedRef.current) return;
        
        const url = URL.createObjectURL(blob);
        if (imgRef.current) {
          // Revoke previous blob URL to avoid memory leak
          const prevSrc = imgRef.current.src;
          imgRef.current.src = url;
          if (prevSrc.startsWith('blob:')) {
            URL.revokeObjectURL(prevSrc);
          }
        }
        
        setStatus(rvizStatus === 'ok' ? 'live' : 'connecting');
      } else {
        setStatus('offline');
      }
    } catch {
      if (mountedRef.current) setStatus('offline');
    }
    
    // Schedule next frame
    if (mountedRef.current) {
      timerRef.current = window.setTimeout(fetchFrame, 150);  // ~7 FPS
    }
  }, [snapshotUrl]);

  useEffect(() => {
    mountedRef.current = true;
    fetchFrame();
    
    return () => {
      mountedRef.current = false;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [fetchFrame]);

  return (
    <div className="w-full h-full relative bg-gray-900 rounded-lg overflow-hidden border border-gray-700 shadow-inner flex items-center justify-center">
      {/* The image — always present */}
      <img
        ref={imgRef}
        alt="RViz Live View"
        className="w-full h-full object-contain"
        style={{ minHeight: '300px' }}
      />

      {/* Overlay label */}
      <div className="absolute top-2 left-2 z-20 flex items-center space-x-2 bg-black/50 px-2 py-1 rounded">
        <div className={`w-2 h-2 rounded-full ${
          status === 'live' ? 'bg-green-500 animate-pulse' : 
          status === 'connecting' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
        }`}></div>
        <span className="text-xs text-gray-300 font-mono">
          {status === 'live' ? 'RViz LIVE' : 
           status === 'connecting' ? 'Waiting for RViz...' : 'OFFLINE'}
        </span>
      </div>

      {/* Offline retry button */}
      {status === 'offline' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 bg-gray-900/80">
          <p className="text-sm text-gray-400 mb-3">RViz stream unavailable</p>
          <button
            onClick={() => { setStatus('connecting'); fetchFrame(); }}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};

export default RobotViewer3D;
