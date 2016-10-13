package eu.nomad_lab.parsers

import eu.{ nomad_lab => lab }
import eu.nomad_lab.{ JsonUtils, DefaultPythonInterpreter }
import org.{ json4s => jn }
import scala.collection.breakOut

object FploParser extends SimpleExternalParserGenerator(
  name = "FploParser",
  parserInfo = jn.JObject(
    ("name" -> jn.JString("FploParser")) ::
      ("parserId" -> jn.JString("FploParser" + lab.FploVersionInfo.version)) ::
      ("versionInfo" -> jn.JObject(
        ("nomadCoreVersion" -> jn.JObject(lab.NomadCoreVersionInfo.toMap.map {
          case (k, v) => k -> jn.JString(v.toString)
        }(breakOut): List[(String, jn.JString)])) ::
          (lab.FploVersionInfo.toMap.map {
            case (key, value) =>
              (key -> jn.JString(value.toString))
          }(breakOut): List[(String, jn.JString)])
      )) :: Nil
  ),
  mainFileTypes = Seq("text/.*"),
  mainFileRe = """\s*\|\s*FULL-POTENTIAL LOCAL-ORBITAL MINIMUM BASIS BANDSTRUCTURE CODE\s*\|\s*\n""".r,
  cmd = Seq(DefaultPythonInterpreter.pythonExe(), "${envDir}/parsers/fplo/parser/parser-fplo/parser_fplo_14.py",
    "--uri", "${mainFileUri}", "${mainFilePath}"),
  resList = Seq(
    "parser-fplo/FploCommon.py",
    "parser-fplo/parser_fplo_14.py",
    "parser-fplo/setup_paths.py",
    "nomad_meta_info/public.nomadmetainfo.json",
    "nomad_meta_info/common.nomadmetainfo.json",
    "nomad_meta_info/meta_types.nomadmetainfo.json",
    "nomad_meta_info/fplo.nomadmetainfo.json",
    "nomad_meta_info/fplo.temporaries.nomadmetainfo.json"
  ) ++ DefaultPythonInterpreter.commonFiles(),
  dirMap = Map(
    "parser-fplo" -> "parsers/fplo/parser/parser-fplo",
    "nomad_meta_info" -> "nomad-meta-info/meta_info/nomad_meta_info",
    "python" -> "python-common/common/python/nomadcore"
  ) ++ DefaultPythonInterpreter.commonDirMapping(),
  metaInfoEnv = Some(lab.meta.KnownMetaInfoEnvs.fplo)
)