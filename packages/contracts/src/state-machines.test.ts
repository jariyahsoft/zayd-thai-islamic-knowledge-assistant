import { describe, expect, it } from "vitest";

import { DocumentStatus, IncidentStatus, ReviewTaskStatus } from "./enums.js";
import {
  InvalidStateTransitionError,
  MissingTransitionMetadataError,
  documentStateMachine,
  incidentStateMachine,
  reviewTaskStateMachine,
} from "./state-machines.js";

describe("TypeScript State Machines", () => {
  describe("documentStateMachine", () => {
    it("allows valid transitions", () => {
      const metadata = {
        actorId: "user-123",
        timestamp: new Date(),
        reason: "Passing review",
      };

      expect(
        documentStateMachine.canTransition(
          DocumentStatus.DRAFT,
          DocumentStatus.UPLOADED
        )
      ).toBe(true);

      // Should not throw
      documentStateMachine.validateTransition(
        DocumentStatus.DRAFT,
        DocumentStatus.UPLOADED,
        metadata
      );
    });

    it("rejects invalid transitions", () => {
      const metadata = {
        actorId: "user-123",
        timestamp: new Date(),
      };

      expect(
        documentStateMachine.canTransition(
          DocumentStatus.DRAFT,
          DocumentStatus.PUBLISHED
        )
      ).toBe(false);

      expect(() => {
        documentStateMachine.validateTransition(
          DocumentStatus.DRAFT,
          DocumentStatus.PUBLISHED,
          metadata
        );
      }).toThrow(InvalidStateTransitionError);
    });

    it("requires reason for sensitive target states", () => {
      const timestamp = new Date();

      // PUBLISHED
      expect(() => {
        documentStateMachine.validateTransition(
          DocumentStatus.SCHOLAR_APPROVED,
          DocumentStatus.PUBLISHED,
          { actorId: "u-1", timestamp }
        );
      }).toThrow(MissingTransitionMetadataError);

      documentStateMachine.validateTransition(
        DocumentStatus.SCHOLAR_APPROVED,
        DocumentStatus.PUBLISHED,
        { actorId: "u-1", timestamp, reason: "Ready for launch" }
      );

      // SUSPENDED
      expect(() => {
        documentStateMachine.validateTransition(
          DocumentStatus.PUBLISHED,
          DocumentStatus.SUSPENDED,
          { actorId: "u-1", timestamp }
        );
      }).toThrow(MissingTransitionMetadataError);

      documentStateMachine.validateTransition(
        DocumentStatus.PUBLISHED,
        DocumentStatus.SUSPENDED,
        { actorId: "u-1", timestamp, reason: "Reported violation" }
      );

      // REJECTED
      expect(() => {
        documentStateMachine.validateTransition(
          DocumentStatus.IN_REVIEW,
          DocumentStatus.REJECTED,
          { actorId: "u-1", timestamp }
        );
      }).toThrow(MissingTransitionMetadataError);

      documentStateMachine.validateTransition(
        DocumentStatus.IN_REVIEW,
        DocumentStatus.REJECTED,
        { actorId: "u-1", timestamp, reason: "Duplicate file" }
      );
    });

    it("identifies terminal states correctly", () => {
      expect(documentStateMachine.isTerminal(DocumentStatus.ARCHIVED)).toBe(
        true
      );
      expect(documentStateMachine.isTerminal(DocumentStatus.REJECTED)).toBe(
        true
      );
      expect(documentStateMachine.isTerminal(DocumentStatus.NEW_VERSION)).toBe(
        true
      );
      expect(documentStateMachine.isTerminal(DocumentStatus.DRAFT)).toBe(false);
    });
  });

  describe("reviewTaskStateMachine", () => {
    it("allows valid review task updates", () => {
      const metadata = { actorId: "r-1", timestamp: new Date() };

      expect(
        reviewTaskStateMachine.canTransition(
          ReviewTaskStatus.OPEN,
          ReviewTaskStatus.IN_PROGRESS
        )
      ).toBe(true);

      // Should not throw
      reviewTaskStateMachine.validateTransition(
        ReviewTaskStatus.OPEN,
        ReviewTaskStatus.IN_PROGRESS,
        metadata
      );
    });

    it("prevents changing completed task status", () => {
      const metadata = { actorId: "r-1", timestamp: new Date() };

      expect(
        reviewTaskStateMachine.canTransition(
          ReviewTaskStatus.COMPLETED,
          ReviewTaskStatus.IN_PROGRESS
        )
      ).toBe(false);

      expect(() => {
        reviewTaskStateMachine.validateTransition(
          ReviewTaskStatus.COMPLETED,
          ReviewTaskStatus.IN_PROGRESS,
          metadata
        );
      }).toThrow(InvalidStateTransitionError);
    });
  });

  describe("incidentStateMachine", () => {
    it("manages incident states", () => {
      const metadata = { actorId: "adm-1", timestamp: new Date() };

      expect(
        incidentStateMachine.canTransition(
          IncidentStatus.OPEN,
          IncidentStatus.TRIAGED
        )
      ).toBe(true);
      expect(
        incidentStateMachine.canTransition(
          IncidentStatus.CLOSED,
          IncidentStatus.OPEN
        )
      ).toBe(true); // Re-open

      // Should not throw
      incidentStateMachine.validateTransition(
        IncidentStatus.OPEN,
        IncidentStatus.TRIAGED,
        metadata
      );
    });
  });
});
