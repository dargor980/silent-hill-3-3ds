#pragma once
#include <QObject>

class Emitter final : public QObject {
    Q_OBJECT
public:
    void publish(int value) { emit delivered(value); }
signals:
    void delivered(int value);
};
