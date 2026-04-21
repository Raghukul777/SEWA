/**
 * useVitalsStream — React hook for real-time vitals via WebSocket
 *
 * Connects once to ws://backend/ws/vitals, subscribes to patient IDs,
 * and calls callbacks for vitals, alerts, and connection status.
 *
 * Handles React StrictMode double-mount gracefully by debouncing
 * the connection and using a stable ref-based approach.
 */

import { useEffect, useRef, useCallback } from 'react';

const WS_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
    .replace(/^http/, 'ws');

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 15;

/**
 * @param {Object}   options
 * @param {string[]} options.patientIds  - Patient IDs to subscribe to
 * @param {Function} options.onVital     - Called with each vital reading
 * @param {Function} options.onAlert     - Called with each alert
 * @param {Function} [options.onStatus]  - Called with connection status changes
 * @param {boolean}  [options.enabled=true]
 */
export function useVitalsStream({ patientIds, onVital, onAlert, onStatus, enabled = true }) {
    const wsRef = useRef(null);
    const reconnectTimerRef = useRef(null);
    const connectDelayRef = useRef(null);
    const attemptsRef = useRef(0);
    const destroyedRef = useRef(false);

    // Store latest callbacks in refs (avoids stale closures and re-connections)
    const latestRef = useRef({ patientIds, onVital, onAlert, onStatus });
    latestRef.current = { patientIds, onVital, onAlert, onStatus };

    const connect = useCallback(() => {
        if (destroyedRef.current) return;
        const token = localStorage.getItem('token');
        if (!token) return;

        const { patientIds: pids } = latestRef.current;
        if (!pids || pids.length === 0) return;

        // Close any existing connection
        if (wsRef.current) {
            console.log('[WS Trace] connect() called but wsRef already exists. Closing existing socket.');
            try { wsRef.current.close(1000); } catch { }
        }

        const url = `${WS_BASE}/ws/vitals?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            attemptsRef.current = 0;
            console.log('[WS] ✓ Connected');

            // Subscribe immediately
            const ids = latestRef.current.patientIds || [];
            if (ids.length > 0) {
                ws.send(JSON.stringify({ type: 'subscribe', patient_ids: ids }));
            }
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                const { onVital: v, onAlert: a, onStatus: s } = latestRef.current;

                switch (msg.type) {
                    case 'vital':
                        v?.(msg.data);
                        break;
                    case 'alert':
                        a?.(msg.data);
                        break;
                    case 'status':
                        s?.(msg.data);
                        break;
                    case 'ping':
                        // Keepalive — ignore
                        break;
                }
            } catch (e) {
                console.warn('[WS] Parse error:', e);
            }
        };

        ws.onerror = () => {
            console.warn('[WS] Connection error');
        };

        ws.onclose = (event) => {
            console.log(`[WS] Disconnected (code ${event.code})`);
            latestRef.current.onStatus?.({ connected: false });

            if (destroyedRef.current) return;
            if (event.code === 4001 || event.code === 4003) return; // Auth failure

            if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
                attemptsRef.current++;
                const delay = RECONNECT_DELAY_MS * Math.min(attemptsRef.current, 5);
                console.log(`[WS] Reconnecting in ${delay}ms (attempt ${attemptsRef.current})`);
                reconnectTimerRef.current = setTimeout(connect, delay);
            }
        };
    }, []);

    useEffect(() => {
        if (!enabled || !patientIds || patientIds.length === 0) return;

        destroyedRef.current = false;

        // Debounce connection by 200ms to handle React StrictMode rapid unmount/remount
        connectDelayRef.current = setTimeout(connect, 200);

        return () => {
            console.log(`[WS Trace] useEffect cleanup running! enabled=${enabled}, patientIds=${patientIds}`);
            destroyedRef.current = true;
            clearTimeout(connectDelayRef.current);
            clearTimeout(reconnectTimerRef.current);
            try { wsRef.current?.close(1000, 'cleanup'); } catch { }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [enabled]);

    // When patient list changes on an already-open connection, update subscription
    useEffect(() => {
        const ws = wsRef.current;
        if (ws?.readyState === WebSocket.OPEN && patientIds?.length > 0) {
            ws.send(JSON.stringify({ type: 'subscribe', patient_ids: patientIds }));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [(patientIds || []).join(',')]);
}
