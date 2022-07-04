DROP TABLE IF EXISTS `user`;
CREATE TABLE IF NOT EXISTS `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `leader_card_id` int  DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB;

-- ROP INDEX IF EXISTS user_token_idx;
CREATE INDEX user_token_idx ON user (token);

DROP TABLE IF EXISTS `room`;
CREATE TABLE IF NOT EXISTS `room` (
  `room_id` bigint NOT NULL AUTO_INCREMENT,
  `live_id` int NOT NULL,
  `host_id` int NOT NULL,
  `room_status` tinyint NOT NULL,
  `joined_user_count` tinyint NOT NULL,
  `max_user_count` tinyint NOT NULL,
  PRIMARY KEY (`room_id`)
) ENGINE=InnoDB;

-- DROP INDEX IF EXISTS room_roomid_idx;
CREATE INDEX room_roomid_idx ON room (room_id);

DROP TABLE IF EXISTS `room_member`;
CREATE TABLE IF NOT EXISTS `room_member` (
  `room_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  `difficulty` tinyint NOT NULL,
  `score` int DEFAULT NULL,
  `perfect` smallint DEFAULT NULL,
  `great` smallint DEFAULT NULL,
  `good` smallint DEFAULT NULL,
  `bad` smallint DEFAULT NULL,
  `miss` smallint DEFAULT NUll,
  PRIMARY KEY (`room_id`,`user_id`)
) ENGINE=InnoDB;



