IF DB_ID('WildlifeDB') IS NULL
BEGIN
    CREATE DATABASE WildlifeDB;
END
GO

USE WildlifeDB;
GO

IF OBJECT_ID('notifications', 'U') IS NOT NULL DROP TABLE notifications;
IF OBJECT_ID('requests', 'U') IS NOT NULL DROP TABLE requests;
IF OBJECT_ID('detections', 'U') IS NOT NULL DROP TABLE detections;
IF OBJECT_ID('devices', 'U') IS NOT NULL DROP TABLE devices;
IF OBJECT_ID('model_runs', 'U') IS NOT NULL DROP TABLE model_runs;
IF OBJECT_ID('images', 'U') IS NOT NULL DROP TABLE images;
IF OBJECT_ID('rangers', 'U') IS NOT NULL DROP TABLE rangers;
IF OBJECT_ID('cameras', 'U') IS NOT NULL DROP TABLE cameras;
IF OBJECT_ID('species', 'U') IS NOT NULL DROP TABLE species;
GO

CREATE TABLE species (
    species_id      INT IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(50) NOT NULL UNIQUE,
    common_name     NVARCHAR(100) NOT NULL
);

CREATE TABLE cameras (
    camera_id             INT IDENTITY(1,1) PRIMARY KEY,
    name                  NVARCHAR(50) NOT NULL UNIQUE,
    location_description  NVARCHAR(255),
    latitude              FLOAT,
    longitude             FLOAT
);

CREATE TABLE rangers (
    ranger_id   INT IDENTITY(1,1) PRIMARY KEY,
    name        NVARCHAR(100) NOT NULL,
    contact     NVARCHAR(255),
    otp         NVARCHAR(10)
);

CREATE TABLE devices (
    device_id       INT IDENTITY(1,1) PRIMARY KEY,
    ranger_id       INT NOT NULL,
    fcm_token       NVARCHAR(255) NOT NULL UNIQUE,
    platform        NVARCHAR(10) NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    registered_at   DATETIME NOT NULL DEFAULT GETDATE(),
    last_active_at  DATETIME NULL,
    platform_version varchar(100),
    CONSTRAINT FK_devices_ranger FOREIGN KEY (ranger_id) REFERENCES rangers(ranger_id)
);

CREATE TABLE images (
    image_id     INT IDENTITY(1,1) PRIMARY KEY,
    camera_id    INT NOT NULL,
    file_path    NVARCHAR(500) NOT NULL UNIQUE,
    captured_at  DATETIME NOT NULL,
    CONSTRAINT FK_images_camera FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);
CREATE INDEX idx_images_camera ON images(camera_id);
CREATE INDEX idx_images_captured_at ON images(captured_at);

CREATE TABLE model_runs (
    model_run_id    INT IDENTITY(1,1) PRIMARY KEY,
    model_version   NVARCHAR(50) NOT NULL,
    quantized       BIT NOT NULL DEFAULT 0,
    size_kb         FLOAT,
    avg_latency_ms  FLOAT,
    accuracy        FLOAT,
    created_at      DATETIME NOT NULL DEFAULT GETDATE()
);

CREATE TABLE detections (
    detection_id       INT IDENTITY(1,1) PRIMARY KEY,
    image_id           INT NOT NULL,
    species_id         INT NOT NULL,
    model_run_id       INT NOT NULL,
    confidence         FLOAT NOT NULL,
    inference_time_ms  FLOAT,
    created_at         DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_detections_image FOREIGN KEY (image_id) REFERENCES images(image_id),
    CONSTRAINT FK_detections_species FOREIGN KEY (species_id) REFERENCES species(species_id),
    CONSTRAINT FK_detections_model_run FOREIGN KEY (model_run_id) REFERENCES model_runs(model_run_id)
);
CREATE INDEX idx_detections_image ON detections(image_id);
CREATE INDEX idx_detections_species ON detections(species_id);
CREATE INDEX idx_detections_created_at ON detections(created_at);

CREATE TABLE requests (
    request_id              INT IDENTITY(1,1) PRIMARY KEY,
    ranger_id                INT NOT NULL,
    species_id                INT NOT NULL,
    camera_id                  INT NULL,
    status                      NVARCHAR(10) NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'seen', 'expired')),
    created_at                  DATETIME NOT NULL DEFAULT GETDATE(),
    fulfilled_at                 DATETIME NULL,
    fulfilled_detection_id        INT NULL,
    CONSTRAINT FK_requests_ranger FOREIGN KEY (ranger_id) REFERENCES rangers(ranger_id),
    CONSTRAINT FK_requests_species FOREIGN KEY (species_id) REFERENCES species(species_id),
    CONSTRAINT FK_requests_camera FOREIGN KEY (camera_id) REFERENCES cameras(camera_id),
    CONSTRAINT FK_requests_detection FOREIGN KEY (fulfilled_detection_id) REFERENCES detections(detection_id)
);
CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_species ON requests(species_id);

CREATE TABLE notifications (
    notification_id     INT IDENTITY(1,1) PRIMARY KEY,
    request_id            INT NOT NULL,
    device_id              INT NOT NULL,
    sent_at                 DATETIME NOT NULL DEFAULT GETDATE(),
    status                   NVARCHAR(10) NOT NULL DEFAULT 'sent'
                             CHECK (status IN ('sent', 'failed')),
    CONSTRAINT FK_notifications_request FOREIGN KEY (request_id) REFERENCES requests(request_id),
    CONSTRAINT FK_notifications_device FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
CREATE INDEX idx_notifications_request ON notifications(request_id);
GO

GO
