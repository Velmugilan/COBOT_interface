import React, { useEffect, useState } from 'react';

const RobotViewer3D = ({ joints }: { joints: Record<string, number> }) => {
  const [imgSrc, setImgSrc] = useState<string>("");
  const [errorCount, setErrorCount] = useState(0);

  useEffect(() => {
    // Poll the snapshot endpoint for live RViz updates
    let isSubscribed = true;
    
    const fetchSnapshot = async () => {
      if (!isSubscribed) return;
      
      try {
        const timestamp = new Date().getTime();
        const url = `http://${window.location.hostname}:8000/api/camera/snapshot?t=${timestamp}`;
        
        // Preload image to avoid flickering
        const img = new Image();
        img.onload = () => {
          if (isSubscribed) {
            setImgSrc(url);
            setErrorCount(0);
            setTimeout(fetchSnapshot, 100); // ~10 FPS for camera
          }
        };
        img.onerror = () => {
          if (isSubscribed) {
            setErrorCount(c => c + 1);
            setTimeout(fetchSnapshot, 1000); // Retry slower on error
          }
        };
        img.src = url;
      } catch (err) {
        if (isSubscribed) {
          setErrorCount(c => c + 1);
          setTimeout(fetchSnapshot, 1000);
        }
      }
    };

    fetchSnapshot();

    return () => {
      isSubscribed = false;
    };
  }, []);

  return (
    <div className="w-full h-full relative bg-gray-900 rounded-lg overflow-hidden border border-gray-700 shadow-inner flex items-center justify-center">
      {imgSrc && errorCount < 3 ? (
        <img 
          src={imgSrc} 
          alt="Robot Camera Feed" 
          className="w-full h-full object-cover rounded-lg"
        />
      ) : (
        <div className="flex flex-col items-center justify-center h-full w-full text-center p-6 text-gray-400">
           <svg className="w-16 h-16 mb-4 text-emerald-500 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
           </svg>
           <h3 className="text-xl font-bold text-white mb-2">Waiting for Camera Feed...</h3>
           <p className="text-sm">Connecting to /wrist_camera/image</p>
        </div>
      )}
    </div>
  );
};

export default RobotViewer3D;
