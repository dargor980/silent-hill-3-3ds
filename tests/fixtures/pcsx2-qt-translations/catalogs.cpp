#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocale>
#include <QTemporaryDir>
#include <QTranslator>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const QString& reason) {
    if (!value) throw std::runtime_error(reason.toStdString());
}

QJsonObject readOracle(const QString& path) {
    QFile file(path);
    require(file.open(QIODevice::ReadOnly), "Cannot read oracle");
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    require(error.error == QJsonParseError::NoError && document.isObject(), "Invalid oracle JSON");
    return document.object();
}

QString qm(const QDir& directory, const QString& name) {
    return directory.filePath(name + ".qm");
}

int compareMessages(QTranslator& translator, const QJsonObject& catalog) {
    const auto messages = catalog["messages"].toArray();
    require(!messages.isEmpty(), "Empty message oracle");
    require(QCoreApplication::installTranslator(&translator), "Cannot install translator");
    int comparisons = 0;
    for (const auto& value : messages) {
        const auto message = value.toObject();
        const auto context = message["context"].toString().toUtf8();
        const auto source = message["source"].toString().toUtf8();
        const auto comment = message["comment"].toString().toUtf8();
        const auto forms = message["values"].toArray();
        const bool plural = message["plural"].toBool();
        const QList<int> numbers = plural ? QList<int>{0, 1, 2, 5} : QList<int>{-1};
        for (const int n : numbers) {
            const auto wanted = forms.at(plural && n != 1 ? 1 : 0).toString();
            const auto actual = translator.translate(context.constData(), source.constData(), comment.constData(), n);
            // Do not expose provider strings in diagnostics; catalog and ordinal identify the input.
            const auto identity = catalog["catalog"].toString() + " comparison " + QString::number(comparisons);
            require(actual == wanted, "Direct translation mismatch: " + identity);
            auto expanded = wanted;
            if (n >= 0) {
                expanded.replace("%Ln", QLocale().toString(n));
                expanded.replace("%n", QString::number(n));
            }
            require(QCoreApplication::translate(context.constData(), source.constData(), comment.constData(), n) == expanded,
                    "Application translation mismatch: " + identity);
            ++comparisons;
        }
    }
    require(QCoreApplication::translate("SH3_Private_Oracle_Missing_Context", "Own fallback text") == "Own fallback text",
            "Missing message fallback failed");
    require(QCoreApplication::removeTranslator(&translator), "Cannot remove translator");
    const auto first = messages.first().toObject();
    const auto context = first["context"].toString().toUtf8();
    const auto source = first["source"].toString().toUtf8();
    const auto comment = first["comment"].toString().toUtf8();
    require(QCoreApplication::translate(context.constData(), source.constData(), comment.constData()) == QString::fromUtf8(source),
            "Fallback after removal failed");
    return comparisons;
}
}

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    QLocale::setDefault(QLocale("es_ES"));
    try {
        require(argc == 4, "Expected case, QM directory, oracle JSON");
        const QString mode = QString::fromLocal8Bit(argv[1]);
        const QDir directory(QString::fromLocal8Bit(argv[2]));
        const auto oracle = readOracle(QString::fromLocal8Bit(argv[3]));
        const auto catalogs = oracle["catalogs"].toArray();
        const auto spanish = oracle["spanish"].toArray();
        require(catalogs.size() > 291 && spanish.size() == 13, "Incomplete oracle");
        int count = 0;
        if (mode == "catalogs") {
            for (const auto& value : catalogs) {
                const auto entry = value.toObject();
                const auto name = entry["catalog"].toString();
                QTranslator translator;
                require(translator.load(qm(directory, name)), "Cannot load " + name);
                require(translator.language() == entry["language"].toString(), "Wrong language: " + name);
                ++count;
            }
        } else if (mode == "spanish") {
            for (const auto& value : spanish) {
                const auto entry = value.toObject();
                if (entry["messages"].toArray().isEmpty()) continue; // Aggregate tested separately.
                QTranslator translator;
                require(translator.load(qm(directory, entry["catalog"].toString())), "Cannot load Spanish QM");
                count += compareMessages(translator, entry);
            }
        } else if (mode == "aggregate") {
            QTranslator translator;
            require(translator.load(qm(directory, "qt_es")), "Cannot load aggregate");
            for (const auto& value : spanish) {
                const auto entry = value.toObject();
                const auto name = entry["catalog"].toString();
                if (name == "qtbase_es" || name == "qtmultimedia_es") count += compareMessages(translator, entry);
            }
            require(count > 1600, "Incomplete aggregate oracle");
        } else if (mode == "recovery") {
            QTemporaryDir temporary;
            require(temporary.isValid(), "Cannot create temporary directory");
            QTranslator translator;
            require(translator.load(qm(directory, "qtbase_es")), "Initial load failed");
            require(!translator.load(temporary.filePath("missing.qm")), "Missing QM accepted");
            require(translator.isEmpty(), "Missing QM retained stale data");
            QFile corrupt(temporary.filePath("corrupt.qm"));
            require(corrupt.open(QIODevice::WriteOnly), "Cannot write corrupt fixture");
            require(corrupt.write("Own invalid QM content") == 22, "Corrupt fixture write failed");
            corrupt.close();
            require(!translator.load(corrupt.fileName()), "Corrupt QM accepted");
            require(translator.isEmpty(), "Corrupt QM retained stale data");
            require(translator.load(qm(directory, "qtbase_es")), "Recovery load failed");
            for (const auto& value : spanish)
                if (value.toObject()["catalog"] == "qtbase_es") count = compareMessages(translator, value.toObject());
        } else if (mode == "missing-dependency") {
            QTemporaryDir temporary;
            require(temporary.isValid(), "Cannot create isolated dependency directory");
            require(QFile::copy(qm(directory, "qt_es"), temporary.filePath("qt_es.qm")), "Cannot copy aggregate");
            QTranslator translator;
            require(!translator.load(temporary.filePath("qt_es.qm")), "Aggregate accepted without dependencies");
            require(translator.isEmpty(), "Incomplete aggregate retained data");
            require(QFile::copy(qm(directory, "qtbase_es"), temporary.filePath("qtbase_es.qm")), "Cannot copy first dependency");
            require(!translator.load(temporary.filePath("qt_es.qm")), "Aggregate accepted with second dependency missing");
            require(translator.isEmpty(), "Partial dependency load retained data");
            require(QFile::copy(qm(directory, "qtmultimedia_es"), temporary.filePath("qtmultimedia_es.qm")), "Cannot copy second dependency");
            require(translator.load(temporary.filePath("qt_es.qm")), "Aggregate recovery failed");
            for (const auto& value : spanish) {
                const auto entry = value.toObject();
                const auto name = entry["catalog"].toString();
                if (name == "qtbase_es" || name == "qtmultimedia_es") count += compareMessages(translator, entry);
            }
        } else {
            throw std::runtime_error("Unknown case");
        }
        require(count > 0, "No checks performed");
        std::cout << mode.toStdString() << " checks=" << count << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
