DROP TRIGGER IF EXISTS trg_answer_invalidations_immutable ON answer_invalidations;
DROP FUNCTION IF EXISTS zayd_reject_answer_invalidation_mutation();
DROP TABLE IF EXISTS answer_invalidations;
