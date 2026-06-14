import { NextResponse } from "next/server";
import { getMergedMissions } from "@/lib/mission-store";

const resolveOperatorAccess = (request: Request): {
  includeInternal: boolean;
  errorResponse: NextResponse | null;
} => {
  const operatorKey = process.env.OPERATOR_ACCESS_KEY;
  if (!operatorKey) {
    return { includeInternal: true, errorResponse: null };
  }

  const providedKey =
    request.headers.get("x-operator-key") ??
    request.headers.get("X-Operator-Key");

  if (!providedKey) {
    return { includeInternal: false, errorResponse: null };
  }

  if (providedKey !== operatorKey) {
    return {
      includeInternal: false,
      errorResponse: NextResponse.json(
        { error: "Invalid operator key" },
        { status: 403 },
      ),
    };
  }

  return { includeInternal: true, errorResponse: null };
};

export async function GET(request: Request) {
  try {
    const { includeInternal, errorResponse } = resolveOperatorAccess(request);
    if (errorResponse) {
      return errorResponse;
    }
    const missions = await getMergedMissions({ includeInternal });
    return NextResponse.json({
      missions,
      visibility: includeInternal ? "operator" : "public",
    });
  } catch (error) {
    console.error("Mission feed GET failed", error);
    return NextResponse.json(
      { error: "Unable to load missions" },
      { status: 500 },
    );
  }
}


