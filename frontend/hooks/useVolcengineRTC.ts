import { useEffect, useRef, useState, useCallback } from "react";
import VERTC, {
  IRTCEngine,
  onUserJoinedEvent,
  onUserLeaveEvent,
  ConnectionStateChangeEvent,
  UserBinaryMessageEvent,
  ConnectionState,
} from "@volcengine/rtc";

export type AIStatus = "disconnected" | "joining" | "joined" | "leaving" | "left";

export type RoomState = {
  roomId: string | null;
  userId: string | null;
  connectionState: ConnectionState;
};

export type Command = {
  userId: string;
  message: ArrayBuffer;
};

export type { UserInfo } from "@volcengine/rtc";

export type UseVolcengineRTC = {
  engine: IRTCEngine | null;
  isConnected: boolean;
  aiStatus: AIStatus;
  roomState: RoomState;
  joinRoom: (token: string, roomId: string, userId: string) => Promise<void>;
  leaveRoom: () => Promise<void>;
  sendCommand: (cmd: Command) => void;
};



export function useVolcengineRTC(): UseVolcengineRTC {
  const engineRef = useRef<IRTCEngine | null>(null);
  const [engine, setEngine] = useState<IRTCEngine | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatus>("disconnected");
  const [roomState, setRoomState] = useState<RoomState>({
    roomId: null,
    userId: null,
    connectionState: ConnectionState.CONNECTION_STATE_DISCONNECTED,
  });

  useEffect(() => {
    const initEngine = () => {
      const appId = process.env.NEXT_PUBLIC_VOLCENGINE_APP_ID || "";
      const newEngine = VERTC.createEngine(appId);

      engineRef.current = newEngine;
      setEngine(newEngine);
      setupEventHandlers(newEngine);

      return newEngine;
    };

    const newEngine = initEngine();

    return () => {
      if (engineRef.current) {
        removeEventHandlers(engineRef.current);
        VERTC.destroyEngine(engineRef.current);
        engineRef.current = null;
        setEngine(null);
        setIsConnected(false);
        setAiStatus("disconnected");
        setRoomState({
          roomId: null,
          userId: null,
          connectionState: ConnectionState.CONNECTION_STATE_DISCONNECTED,
        });
      }
    };
  }, []);

  const setupEventHandlers = useCallback((eng: IRTCEngine) => {
    eng.on(VERTC.events.onUserJoined, (event: onUserJoinedEvent) => {
      console.log("[RTC] User joined:", event.userInfo.userId);
      if (event.userInfo.userId === "ai_agent") {
        setAiStatus("joined");
      }
    });

    eng.on(VERTC.events.onUserLeave, (event: onUserLeaveEvent) => {
      console.log("[RTC] User left:", event.userInfo.userId, "reason:", event.reason);
      if (event.userInfo.userId === "ai_agent") {
        setAiStatus("left");
      }
    });

    eng.on(
      VERTC.events.onUserBinaryMessageReceived,
      (event: UserBinaryMessageEvent) => {
        console.log("[RTC] Binary message from:", event.userId);
      }
    );

    eng.on(VERTC.events.onConnectionStateChanged, (event: ConnectionStateChangeEvent) => {
      console.log("[RTC] Connection state:", event.state);
      if (event.state === ConnectionState.CONNECTION_STATE_DISCONNECTED) {
        setIsConnected(false);
        setRoomState((prev) => ({
          ...prev,
          connectionState: ConnectionState.CONNECTION_STATE_DISCONNECTED,
        }));
      }
    });
  }, []);

  const removeEventHandlers = useCallback((eng: IRTCEngine) => {
    eng.off(VERTC.events.onUserJoined);
    eng.off(VERTC.events.onUserLeave);
    eng.off(VERTC.events.onUserBinaryMessageReceived);
    eng.off(VERTC.events.onConnectionStateChanged);
  }, []);

  const joinRoom = useCallback(
    async (token: string, roomId: string, userId: string) => {
      if (!engineRef.current) {
        throw new Error("RTC engine not initialized");
      }

      setRoomState((prev) => ({
        ...prev,
        connectionState: ConnectionState.CONNECTION_STATE_CONNECTING,
      }));

      try {
        await engineRef.current.joinRoom(token, roomId, { userId });
        
        setIsConnected(true);
        setRoomState({
          roomId,
          userId,
          connectionState: ConnectionState.CONNECTION_STATE_CONNECTED,
        });
        setAiStatus("joining");

        console.log("[RTC] Joined room:", roomId, "as user:", userId);
      } catch (error) {
        console.error("[RTC] Failed to join room:", error);
        setRoomState((prev) => ({
          ...prev,
          connectionState: ConnectionState.CONNECTION_STATE_DISCONNECTED,
        }));
        throw error;
      }
    },
    []
  );

  const leaveRoom = useCallback(async () => {
    if (!engineRef.current) {
      return;
    }

    setAiStatus("leaving");
    setRoomState((prev) => ({
      ...prev,
      connectionState: ConnectionState.CONNECTION_STATE_DISCONNECTED,
    }));

    try {
      await engineRef.current.leaveRoom();
      console.log("[RTC] Left room successfully");
    } catch (error) {
      console.error("[RTC] Error leaving room:", error);
    } finally {
      setIsConnected(false);
      setAiStatus("left");
      setRoomState({
        roomId: null,
        userId: null,
        connectionState: ConnectionState.CONNECTION_STATE_DISCONNECTED,
      });
    }
  }, []);

  const sendCommand = useCallback((cmd: Command) => {
    if (!engineRef.current) {
      console.warn("[RTC] Engine not initialized, cannot send command");
      return;
    }

    if (!isConnected) {
      console.warn("[RTC] Not connected, cannot send command");
      return;
    }

    try {
      engineRef.current.sendUserBinaryMessage(
        cmd.userId,
        cmd.message
      );
      console.log("[RTC] Sent command to:", cmd.userId);
    } catch (error) {
      console.error("[RTC] Failed to send command:", error);
    }
  }, [isConnected]);

  return {
    engine,
    isConnected,
    aiStatus,
    roomState,
    joinRoom,
    leaveRoom,
    sendCommand,
  };
}
