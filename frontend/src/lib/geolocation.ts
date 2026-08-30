/**
 * Geolocation helper.
 *
 * Uses the browser Geolocation API to get the user''s coordinates, then
 * reverse-geocodes them to a human-readable address via OpenStreetMap
 * Nominatim (free, no API key required).
 *
 * NOTE: The Geolocation API only works on HTTPS or localhost.
 * Accuracy depends on the device: GPS (~5m), WiFi (~50m), or IP (~km).
 */

export interface LiveLocation {
  address: string;
  latitude: number;
  longitude: number;
  accuracy: number; // meters
}

function getCurrentPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("Geolocation is not supported by this browser."));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 20000,
      maximumAge: 0,
    });
  });
}

async function reverseGeocode(lat: number, lon: number): Promise<string> {
  // zoom=18 requests the most detailed (building/street) level address.
  const url =
    `https://nominatim.openstreetmap.org/reverse?format=jsonv2` +
    `&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`;
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error("Reverse geocoding failed.");
  }
  const data = await res.json();
  return data.display_name || `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
}

export async function getLiveLocation(): Promise<LiveLocation> {
  const position = await getCurrentPosition();
  const { latitude, longitude, accuracy } = position.coords;
  const address = await reverseGeocode(latitude, longitude);
  return { address, latitude, longitude, accuracy };
}

export function geolocationErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "code" in err) {
    const code = (err as GeolocationPositionError).code;
    if (code === 1) return "Location permission denied. Please allow location access.";
    if (code === 2) return "Location unavailable. Please try again.";
    if (code === 3) return "Location request timed out. Please try again.";
  }
  if (err instanceof Error) return err.message;
  return "Could not get your location.";
}
