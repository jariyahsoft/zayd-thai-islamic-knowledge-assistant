import { DocumentStatus, IncidentStatus, ReviewTaskStatus } from "./enums.js";

export interface TransitionMetadata {
  readonly actorId: string;
  readonly timestamp: Date;
  readonly reason?: string;
  readonly notes?: string;
}

export type StateTransitionsMap<T extends string> = Record<T, ReadonlySet<T>>;

export class StateTransitionError extends Error {
  constructor(public readonly errorCode: string, message: string) {
    super(message);
    this.name = "StateTransitionError";
  }
}

export class InvalidStateTransitionError extends StateTransitionError {
  constructor(
    errorCode: string,
    public readonly fromState: string,
    public readonly toState: string
  ) {
    super(errorCode, `Invalid state transition from '${fromState}' to '${toState}'.`);
    this.name = "InvalidStateTransitionError";
  }
}

export class MissingTransitionMetadataError extends StateTransitionError {
  constructor(message: string) {
    super("MISSING_TRANSITION_METADATA", message);
    this.name = "MissingTransitionMetadataError";
  }
}

export abstract class BaseStateMachine<T extends string> {
  protected abstract readonly transitions: StateTransitionsMap<T>;
  protected abstract readonly errorCode: string;

  public canTransition(fromState: T, toState: T): boolean {
    const allowed = this.transitions[fromState];
    return allowed ? allowed.has(toState) : false;
  }

  public getAllowedTransitions(fromState: T): ReadonlySet<T> {
    return this.transitions[fromState] || new Set();
  }

  public isTerminal(state: T): boolean {
    return this.getAllowedTransitions(state).size === 0;
  }

  public validateTransition(
    fromState: T,
    toState: T,
    metadata: TransitionMetadata
  ): void {
    if (!this.canTransition(fromState, toState)) {
      throw new InvalidStateTransitionError(this.errorCode, fromState, toState);
    }
    if (!metadata.actorId || metadata.actorId.trim().length === 0) {
      throw new MissingTransitionMetadataError("Actor ID is required for state transition.");
    }
    if (!metadata.timestamp) {
      throw new MissingTransitionMetadataError("Timestamp is required for state transition.");
    }
  }
}

export class DocumentStateMachineClass extends BaseStateMachine<DocumentStatus> {
  protected readonly errorCode = "DOCUMENT_INVALID_TRANSITION";
  protected readonly transitions: StateTransitionsMap<DocumentStatus> = {
    [DocumentStatus.DRAFT]: new Set([DocumentStatus.UPLOADED]),
    [DocumentStatus.UPLOADED]: new Set([DocumentStatus.PARSING]),
    [DocumentStatus.PARSING]: new Set([DocumentStatus.AI_EXTRACTED, DocumentStatus.REJECTED]),
    [DocumentStatus.AI_EXTRACTED]: new Set([DocumentStatus.IN_REVIEW]),
    [DocumentStatus.IN_REVIEW]: new Set([
      DocumentStatus.CHANGES_REQUESTED,
      DocumentStatus.REJECTED,
      DocumentStatus.SCHOLAR_REVIEW,
    ]),
    [DocumentStatus.CHANGES_REQUESTED]: new Set([DocumentStatus.IN_REVIEW]),
    [DocumentStatus.SCHOLAR_REVIEW]: new Set([
      DocumentStatus.CHANGES_REQUESTED,
      DocumentStatus.REJECTED,
      DocumentStatus.SCHOLAR_APPROVED,
    ]),
    [DocumentStatus.SCHOLAR_APPROVED]: new Set([DocumentStatus.PUBLISHED]),
    [DocumentStatus.PUBLISHED]: new Set([
      DocumentStatus.SUSPENDED,
      DocumentStatus.ARCHIVED,
      DocumentStatus.NEW_VERSION,
    ]),
    [DocumentStatus.SUSPENDED]: new Set([
      DocumentStatus.PUBLISHED,
      DocumentStatus.ARCHIVED,
      DocumentStatus.NEW_VERSION,
    ]),
    [DocumentStatus.ARCHIVED]: new Set(),
    [DocumentStatus.REJECTED]: new Set(),
    [DocumentStatus.NEW_VERSION]: new Set(),
  };

  public validateTransition(
    fromState: DocumentStatus,
    toState: DocumentStatus,
    metadata: TransitionMetadata
  ): void {
    super.validateTransition(fromState, toState, metadata);
    if (
      toState === DocumentStatus.PUBLISHED ||
      toState === DocumentStatus.SUSPENDED ||
      toState === DocumentStatus.REJECTED
    ) {
      if (!metadata.reason || metadata.reason.trim().length === 0) {
        throw new MissingTransitionMetadataError(
          `A non-empty reason is required to transition to '${toState}' status.`
        );
      }
    }
  }
}

export class ReviewTaskStateMachineClass extends BaseStateMachine<ReviewTaskStatus> {
  protected readonly errorCode = "REVIEW_TASK_INVALID_TRANSITION";
  protected readonly transitions: StateTransitionsMap<ReviewTaskStatus> = {
    [ReviewTaskStatus.OPEN]: new Set([
      ReviewTaskStatus.IN_PROGRESS,
      ReviewTaskStatus.COMPLETED,
      ReviewTaskStatus.CANCELLED,
    ]),
    [ReviewTaskStatus.IN_PROGRESS]: new Set([
      ReviewTaskStatus.COMPLETED,
      ReviewTaskStatus.CANCELLED,
    ]),
    [ReviewTaskStatus.COMPLETED]: new Set(),
    [ReviewTaskStatus.CANCELLED]: new Set(),
  };
}

export class IncidentStateMachineClass extends BaseStateMachine<IncidentStatus> {
  protected readonly errorCode = "INCIDENT_INVALID_TRANSITION";
  protected readonly transitions: StateTransitionsMap<IncidentStatus> = {
    [IncidentStatus.OPEN]: new Set([IncidentStatus.TRIAGED, IncidentStatus.CLOSED]),
    [IncidentStatus.TRIAGED]: new Set([IncidentStatus.MITIGATED, IncidentStatus.CLOSED]),
    [IncidentStatus.MITIGATED]: new Set([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]),
    [IncidentStatus.RESOLVED]: new Set([IncidentStatus.CLOSED]),
    [IncidentStatus.CLOSED]: new Set([IncidentStatus.OPEN]),
  };
}

export const documentStateMachine = new DocumentStateMachineClass();
export const reviewTaskStateMachine = new ReviewTaskStateMachineClass();
export const incidentStateMachine = new IncidentStateMachineClass();
