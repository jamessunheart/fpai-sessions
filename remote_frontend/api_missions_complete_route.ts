import { NextResponse } from "next/server";
import {
  MissionStateError,
  completeMission,
  isMissionStateError,
} from "@/lib/mission-store";

const resolveInternalAccess = (request: Request): {
  allowInternal: boolean;
  errorResponse: NextResponse | null;
} => {
  const operatorKey = process.env.OPERATOR_ACCESS_KEY;
  if (!operatorKey) {
    return { allowInternal: true, errorResponse: null };
  }

  const providedKey =
    request.headers.get("x-operator-key") ??
    request.headers.get("X-Operator-Key");

  if (!providedKey) {
    return { allowInternal: false, errorResponse: null };
  }

  if (providedKey !== operatorKey) {
    return {
      allowInternal: false,
      errorResponse: NextResponse.json(
        { error: "Invalid operator key" },
        { status: 403 },
      ),
    };
  }

  return { allowInternal: true, errorResponse: null };
};

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const missionId = payload?.missionId as string | undefined;
    const actor = payload?.actor as string | undefined;
    const notes = payload?.notes as string | undefined;

    if (!missionId || !actor) {
      return NextResponse.json(
        { error: "missionId and actor are required" },
        { status: 400 },
      );
    }

    const { allowInternal, errorResponse } = resolveInternalAccess(request);
    if (errorResponse) {
      return errorResponse;
    }

    const mission = await completeMission({
      missionId,
      actor,
      notes,
      allowInternal,
    });
    return NextResponse.json({ mission });
  } catch (error) {
    if (isMissionStateError(error)) {
      return NextResponse.json(
        { error: (error as MissionStateError).message },
        { status: (error as MissionStateError).status ?? 400 },
      );
    }

    console.error("Mission completion failed", error);
    return NextResponse.json(
      { error: "Unable to complete mission" },
      { status: 500 },
    );
  }
}


