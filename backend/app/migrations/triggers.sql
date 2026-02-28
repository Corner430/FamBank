-- Audit immutability triggers: prevent UPDATE and DELETE on transaction_log
-- Constitution Principle V: 审计可追溯 — logs are append-only

DELIMITER $$

CREATE TRIGGER trg_transaction_log_no_update
BEFORE UPDATE ON transaction_log
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'AUDIT VIOLATION: transaction_log records cannot be updated';
END$$

CREATE TRIGGER trg_transaction_log_no_delete
BEFORE DELETE ON transaction_log
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'AUDIT VIOLATION: transaction_log records cannot be deleted';
END$$

DELIMITER ;
