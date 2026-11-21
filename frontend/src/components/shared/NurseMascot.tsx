/**
 * NurseMascot: wraps `page-mascot` with sheet preloading, a soft entrance,
 * an idle float and hover/press easing. Motion is transform/opacity only and
 * is disabled under prefers-reduced-motion (see globals.css).
 */
import { useEffect, useState } from "react";
import { Mascot } from "page-mascot";

const DIRECTIONS = "/mascots/nurse-directions.webp";
const REACTIONS = "/mascots/nurse-reactions.webp";
const SIZE = 112;

function preload(src: string): Promise<void> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = img.onerror = () => resolve();
    img.src = src;
    if (img.decode) img.decode().then(() => resolve(), () => resolve());
  });
}

export function NurseMascot() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([preload(DIRECTIONS), preload(REACTIONS)]).then(() => {
      if (!cancelled) setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // The box is reserved up front so nothing shifts when the sheets arrive.
  return (
    <div
      className="-mb-3 flex justify-center"
      style={{ height: SIZE, maxWidth: "100%" }}
    >
      {ready && (
        <div className="mascot-enter">
          <div className="mascot-float">
            <div className="mascot-hover">
              <Mascot
                directions={DIRECTIONS}
                reactions={REACTIONS}
                size={SIZE}
                label="DPDP Healthcare nurse mascot"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}